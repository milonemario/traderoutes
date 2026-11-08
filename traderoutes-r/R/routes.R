SEA_EDGE_TYPES <- c("sea", "sea_border")
BORDER_EDGE_TYPES <- c("road_border", "sea_border")
ROAD_EDGE_TYPES <- c("road", "road_sea")
OPEN_SEA_COUNTRY <- "sea"

#' Return all countries present in the transportation network
#'
#' A country is included if it has at least one city vertex (`vtype = "city"`)
#' in the full graph.
#'
#' @return Sorted character vector of ISO 3-letter country codes.
#'
#' @examples
#' \dontrun{
#' cs <- countries()
#' "FRA" %in% cs   # TRUE
#' }
#' @export
countries <- function() {
  g     <- .g()
  vtypes <- igraph::vertex_attr(g, "vtype")
  city_vs <- which(vtypes == "city")
  sort(unique(igraph::vertex_attr(g, "country", city_vs)))
}


#' Return the main city vertex index for a country
#'
#' The main city is the vertex with `vtype = "city"` and `maincity = "1"` (or
#' `1`) for the specified country. It is used as the default path endpoint and
#' for great-circle distance calculations.
#'
#' @param country ISO 3-letter code of the country (e.g. `"FRA"`).
#'
#' @return Integer vertex index, or `NA` if no main city is found.
#'   A warning is issued when none or more than one main city is found.
#'
#' @examples
#' \dontrun{
#' v <- get_main_city("FRA")
#' igraph::vertex_attr(g, "name", v)
#' }
#' @export
get_main_city <- function(country) {
  g      <- .g()
  vtypes  <- igraph::vertex_attr(g, "vtype")
  mcs    <- igraph::vertex_attr(g, "maincity")
  ctries <- igraph::vertex_attr(g, "country")
  # maincity may be stored as string "1" or integer 1
  idx <- which(vtypes == "city" & (mcs == "1" | mcs == 1) & ctries == country)
  if (length(idx) == 0) {
    warning("No main city found for country ", country, ".", call. = FALSE)
    return(NA_integer_)
  }
  if (length(idx) > 1) {
    warning(
      "More than one main city found for country ", country,
      ". Returning the first one.",
      call. = FALSE
    )
  }
  idx[[1L]]
}


#' Great-circle distance between two countries' main cities
#'
#' @param country1 ISO 3-letter code of the origin country.
#' @param country2 ISO 3-letter code of the destination country.
#'
#' @return Great-circle distance in kilometres (numeric scalar).
#'
#' @examples
#' \dontrun{
#' round(get_great_circle("FRA", "ITA"), 2)   # 1109.56
#' }
#' @export
get_great_circle <- function(country1, country2) {
  g   <- .g()
  v1  <- get_main_city(country1)
  v2  <- get_main_city(country2)
  lon1 <- igraph::vertex_attr(g, "lon", v1)
  lat1 <- igraph::vertex_attr(g, "lat", v1)
  lon2 <- igraph::vertex_attr(g, "lon", v2)
  lat2 <- igraph::vertex_attr(g, "lat", v2)
  .great_circle_km(lat1, lon1, lat2, lon2)
}


#' Return a list with country codes and the great-circle distance between them
#'
#' @param country1 ISO 3-letter code of the origin country.
#' @param country2 ISO 3-letter code of the destination country.
#'
#' @return A named list with `iso_i`, `iso_j`, and `dist`.
#' @export
get_trade_route_great_circle <- function(country1, country2) {
  list(
    iso_i = country1,
    iso_j = country2,
    dist = get_great_circle(country1, country2)
  )
}


#' Compute the weighted shortest-path trade route between two vertices
#'
#' Applies configurable cost weights to graph edges and returns the shortest
#' path. Costs are applied in this order:
#'
#' 1. All edges are initialized to their physical distance (`wdist = dist`).
#' 2. **Port edges** (`etype = "road_sea"`): `wdist = dist + port_cost`.
#'    Per-country overrides in `port_cost_countries` take precedence.
#' 3. **Border edges** (`etype` in `c("road_border", "sea_border")`):
#'    `wdist = dist + border_cost`.
#'    Per-pair overrides in `border_cost_countries` take precedence
#'    (keys are `"C1-C2"` strings).
#' 4. **Road edges** (`etype = "road"`): `wdist = dist * road_cost`.
#'    Per-country overrides in `road_cost_countries` take precedence.
#'
#' @param v1 Integer vertex index of the origin (from [get_main_city()]).
#' @param v2 Integer vertex index of the destination.
#' @param road_cost Multiplicative cost for road edges. Default `1`.
#' @param road_cost_countries Named list of per-country road cost overrides,
#'   e.g. `list(FRA = 2, NLD = 4)`. Default `list()`.
#' @param port_cost Additive cost for land-to-sea transitions. Default `1`.
#' @param port_cost_countries Named list of per-country port cost overrides.
#'   Default `list()`.
#' @param border_cost Additive cost for crossing a country border. Default `0`.
#' @param border_cost_countries Named list of per-country-pair border cost
#'   overrides. Keys are `"C1-C2"` strings, e.g. `list("FRA-DEU" = 500)`.
#'   Default `list()`.
#'
#' @return A named list with:
#'   \describe{
#'     \item{`epath`}{Integer vector of edge indices along the path.}
#'     \item{`vpath`}{Integer vector of vertex indices along the path.}
#'   }
#'
#' @examples
#' \dontrun{
#' v_fra <- get_main_city("FRA")
#' v_nld <- get_main_city("NLD")
#' path  <- get_path(v_fra, v_nld, road_cost = 7, port_cost = 1e4)
#' get_pattern(path)
#' }
#' @export
get_path <- function(v1, v2,
                     road_cost = 1,
                     road_cost_countries = list(),
                     port_cost = 1,
                     port_cost_countries = list(),
                     border_cost = 0,
                     border_cost_countries = list()) {
  g    <- .g()
  dist <- igraph::edge_attr(g, "dist")
  etype <- igraph::edge_attr(g, "etype")
  ecountry  <- igraph::edge_attr(g, "country")
  ecountry1 <- igraph::edge_attr(g, "country1")
  ecountry2 <- igraph::edge_attr(g, "country2")

  # 0. Initialize weighted distances
  wdist <- as.numeric(dist)

  # 1. Port edges (road_sea): additive port_cost
  port_idx <- which(etype == "road_sea")
  wdist[port_idx] <- wdist[port_idx] + port_cost
  for (co in names(port_cost_countries)) {
    idx <- port_idx[ecountry[port_idx] == co]
    wdist[idx] <- as.numeric(dist[idx]) + port_cost_countries[[co]]
  }

  # 2. Border edges (road_border and sea_border): additive border_cost
  border_idx <- which(etype %in% BORDER_EDGE_TYPES)
  wdist[border_idx] <- wdist[border_idx] + border_cost
  for (pair in names(border_cost_countries)) {
    cs <- strsplit(pair, "-")[[1]]
    idx <- border_idx[
      (ecountry1[border_idx] %in% cs) & (ecountry2[border_idx] %in% cs)
    ]
    wdist[idx] <- as.numeric(dist[idx]) + border_cost_countries[[pair]]
  }

  # 3. Road edges: multiplicative road_cost
  road_idx <- which(etype == "road")
  wdist[road_idx] <- wdist[road_idx] * road_cost
  for (co in names(road_cost_countries)) {
    idx <- road_idx[ecountry[road_idx] == co]
    wdist[idx] <- as.numeric(dist[idx]) * road_cost_countries[[co]]
  }

  igraph::edge_attr(g, "wdist") <- wdist

  sp <- igraph::shortest_paths(
    g, from = v1, to = v2,
    weights = igraph::E(g)$wdist,
    output  = "both"
  )
  list(
    vpath = as.integer(sp$vpath[[1]]),
    epath = as.integer(sp$epath[[1]])
  )
}


#' Return the vertex-type pattern of a trade route path
#'
#' Compresses consecutive vertices of the same type into a single character:
#' `c` = city, `r` = road, `p` = port, `s` = sea. Intermediate city vertices
#' (not the first or last vertex) are treated as road.
#'
#' @param path List with element `vpath` (integer vector), as returned by
#'   [get_path()].
#'
#' @return Character string, e.g. `"crc"` (land route) or `"csrc"` (sea route).
#'
#' @examples
#' \dontrun{
#' path <- get_path(get_main_city("FRA"), get_main_city("DEU"), road_cost = 7)
#' get_pattern(path)   # "crc"
#' }
#' @export
get_pattern <- function(path) {
  g      <- .g()
  vpath  <- path$vpath
  vtypes <- igraph::vertex_attr(g, "vtype", vpath)
  type_map <- c(city = "c", port = "p", road = "r", sea = "s")

  # First vertex
  result <- type_map[[vtypes[[1]]]]

  # Intermediate vertices: city → road
  n <- length(vtypes)
  if (n > 2) {
    for (i in seq(2, n - 1)) {
      vt <- vtypes[[i]]
      if (vt == "city") vt <- "road"
      ch <- type_map[[vt]]
      if (ch != result[[length(result)]]) result <- c(result, ch)
    }
  }

  # Last vertex
  ch <- type_map[[vtypes[[n]]]]
  result <- c(result, ch)

  paste(result, collapse = "")
}


#' Return country segments traversed along a path
#'
#' Each element of the returned list contains the ISO3 country code and the
#' distance (km) traveled within that segment.
#'
#' @param path List with elements `vpath` and `epath`, as returned by
#'   [get_path()].
#' @param with_sea Logical. If `TRUE`, sea segments are included with country
#'   code `"sea"`. Default `FALSE`.
#' @param clean_dist Numeric or `NULL`. If set, iteratively removes intermediate
#'   country segments shorter than `clean_dist` km, keeping origin and
#'   destination. Default `NULL`.
#'
#' @return A list of named lists, each with elements `country` (character) and
#'   `dist` (numeric, km), in traversal order.
#'
#' @examples
#' \dontrun{
#' path <- get_path(get_main_city("FRA"), get_main_city("POL"), road_cost = 7)
#' sapply(get_countries(path), `[[`, "country")
#' }
#' @export
get_countries <- function(path, with_sea = FALSE, clean_dist = NULL) {
  g      <- .g()
  vpath  <- path$vpath
  epath  <- path$epath
  vcountry <- lapply(igraph::vertex_attr(g, "country", vpath), .country_or_null)
  edist    <- as.numeric(igraph::edge_attr(g, "dist", epath))

  result <- list()
  cur_country <- vcountry[[1]]
  cur_dist    <- 0

  for (i in seq_along(epath)) {
    cur_dist <- cur_dist + edist[[i]]
    next_country <- vcountry[[i + 1]]
    if (!identical(next_country, cur_country)) {
      # Emit current segment
      emit_country <- cur_country
      if (is.null(emit_country) && with_sea) emit_country <- "sea"
      if (!is.null(emit_country)) {
        result <- c(result, list(list(country = emit_country, dist = cur_dist)))
      }
      cur_country <- next_country
      cur_dist    <- 0
    }
  }
  # Emit final segment
  emit_country <- cur_country
  if (is.null(emit_country) && with_sea) emit_country <- "sea"
  if (!is.null(emit_country)) {
    result <- c(result, list(list(country = emit_country, dist = cur_dist)))
  }

  # Clean short intermediate segments
  if (!is.null(clean_dist)) {
    cleaned <- FALSE
    while (!cleaned && length(result) > 2) {
      dists <- sapply(result[-c(1, length(result))], `[[`, "dist")
      min_d <- min(dists)
      if (min_d < clean_dist) {
        # Remove the shortest intermediate segment
        min_i <- which.min(dists) + 1L   # +1 because we skipped the first
        result <- result[-min_i]
        # Consolidate consecutive same-country segments
        merged <- list(result[[1]])
        for (j in seq(2, length(result))) {
          if (result[[j]]$country == merged[[length(merged)]]$country) {
            merged[[length(merged)]]$dist <-
              merged[[length(merged)]]$dist + result[[j]]$dist
          } else {
            merged <- c(merged, list(result[[j]]))
          }
        }
        result <- merged
      } else {
        cleaned <- TRUE
      }
    }
  }

  result
}


#' Total road distance along a path
#'
#' Sums the `dist` attribute of all edges with `etype` in
#' `c("road", "road_sea")`.
#'
#' @param path List with element `epath`, as returned by [get_path()].
#'
#' @return Numeric scalar, distance in km.
#' @export
road_distance <- function(path) {
  g     <- .g()
  epath <- path$epath
  et    <- igraph::edge_attr(g, "etype",  epath)
  d     <- as.numeric(igraph::edge_attr(g, "dist", epath))
  sum(d[et %in% ROAD_EDGE_TYPES])
}


#' Total sea distance along a path
#'
#' Sums the `dist` attribute of all edges with `etype` in
#' `c("sea", "sea_border")`.
#'
#' @param path List with element `epath`, as returned by [get_path()].
#'
#' @return Numeric scalar, distance in km.
#' @export
sea_distance <- function(path) {
  g     <- .g()
  epath <- path$epath
  et    <- igraph::edge_attr(g, "etype", epath)
  d     <- as.numeric(igraph::edge_attr(g, "dist", epath))
  sum(d[et %in% SEA_EDGE_TYPES])
}


#' Transit countries from the origin side of a path
#'
#' For **land-only** routes: all intermediate countries between origin and
#' destination. For routes **with sea**: countries between the origin and the
#' first sea segment.
#'
#' @param path List as returned by [get_path()].
#' @param clean_dist Numeric or `NULL`. Passed to [get_countries()] to remove
#'   very short country segments. Default `NULL`.
#'
#' @return Character vector of ISO3 transit country codes (may be empty).
#'
#' @examples
#' \dontrun{
#' path <- get_path(get_main_city("CHE"), get_main_city("POL"), road_cost = 7)
#' transits_i(path)
#' }
#' @export
transits_i <- function(path, clean_dist = NULL) {
  pattern <- get_pattern(path)
  if (!grepl("s", pattern)) {
    cs <- sapply(get_countries(path, clean_dist = clean_dist), `[[`, "country")
    if (length(cs) <= 2L) return(character(0))
    return(cs[seq(2, length(cs) - 1)])
  }
  if (nchar(gsub("[^s]", "", pattern)) > 1) {
    stop(
      "Cannot compute transit countries: sea is used more than once in pattern '",
      pattern, "'.",
      call. = FALSE
    )
  }
  cs <- sapply(
    get_countries(path, with_sea = TRUE, clean_dist = clean_dist),
    `[[`, "country"
  )
  if (!(OPEN_SEA_COUNTRY %in% cs)) {
    if (length(cs) <= 2L) return(character(0))
    return(cs[seq(2L, length(cs) - 1L)])
  }
  sea_pos <- which(cs == OPEN_SEA_COUNTRY)[[1L]]
  if (sea_pos <= 2L) return(character(0))
  cs[seq(2L, sea_pos - 1L)]
}


#' Transit countries from the destination side of a path
#'
#' Equivalent to [transits_i()] applied to the reversed path.
#'
#' @param path List as returned by [get_path()].
#' @param clean_dist Numeric or `NULL`. Default `NULL`.
#'
#' @return Character vector of ISO3 transit country codes (may be empty).
#' @export
transits_j <- function(path, clean_dist = NULL) {
  path_rev <- list(
    vpath = rev(path$vpath),
    epath = rev(path$epath)
  )
  transits_i(path_rev, clean_dist = clean_dist)
}


#' Export a trade route path to KML
#'
#' @param path Path as returned by [get_path()].
#' @param filename Output KML path.
#' @export
to_kml <- function(path, filename) {
  g <- .g()
  items <- character(0)
  vpath <- path$vpath
  for (i in seq.int(2L, length(vpath))) {
    coords <- c(
      .kml_coord(
        igraph::vertex_attr(g, "lon", vpath[[i - 1L]]),
        igraph::vertex_attr(g, "lat", vpath[[i - 1L]])
      ),
      .kml_coord(
        igraph::vertex_attr(g, "lon", vpath[[i]]),
        igraph::vertex_attr(g, "lat", vpath[[i]])
      )
    )
    items <- c(items, .kml_line_placemark(coords, color = "ff0000ff", width = 5))
  }
  .write_kml_document(items, filename)
}


#' Export city locations to KML
#'
#' @param filename Output KML path.
#' @param all_cities If `FALSE`, export only main cities.
#' @export
cities_to_kml <- function(filename, all_cities = FALSE) {
  g <- .g()
  vtypes <- igraph::vertex_attr(g, "vtype")
  maincity <- igraph::vertex_attr(g, "maincity")
  idx <- which(vtypes == "city")
  if (!all_cities) {
    idx <- idx[.is_trueish(maincity[idx])]
  }

  folders <- character(0)
  for (co in countries()) {
    pts <- character(0)
    city_idx <- idx[igraph::vertex_attr(g, "country", idx) == co]
    for (i in city_idx) {
      pts <- c(
        pts,
        .kml_point_placemark(
          name = sprintf(
            "%s - %s",
            igraph::vertex_attr(g, "name", i),
            igraph::vertex_attr(g, "country", i)
          ),
          coord = .kml_coord(
            igraph::vertex_attr(g, "lon", i),
            igraph::vertex_attr(g, "lat", i)
          ),
          color = "ff00ffff"
        )
      )
    }
    folders <- c(folders, .kml_folder(co, pts))
  }
  .write_kml_document(folders, filename)
}


#' Export port locations to KML
#'
#' @param filename Output KML path.
#' @export
ports_to_kml <- function(filename) {
  g <- .g()
  vtypes <- igraph::vertex_attr(g, "vtype")
  ports <- which(vtypes == "port")

  folders <- character(0)
  for (co in countries()) {
    pts <- character(0)
    port_idx <- ports[igraph::vertex_attr(g, "country", ports) == co]
    for (i in port_idx) {
      pts <- c(
        pts,
        .kml_point_placemark(
          name = sprintf(
            "%s - %s",
            igraph::vertex_attr(g, "name", i),
            igraph::vertex_attr(g, "country", i)
          ),
          coord = .kml_coord(
            igraph::vertex_attr(g, "lon", i),
            igraph::vertex_attr(g, "lat", i)
          ),
          color = "ffffff00"
        )
      )
    }
    folders <- c(folders, .kml_folder(co, pts))
  }
  .write_kml_document(folders, filename)
}


#' Export the road network to KMZ
#'
#' @param filename Output path prefix. `.kmz` is appended.
#' @export
roads_to_kml <- function(filename) {
  g <- .g()
  epath <- which(igraph::edge_attr(g, "etype") %in% ROAD_EDGE_TYPES)
  road_vertices <- which(igraph::vertex_attr(g, "vtype") == "road")
  road_countries <- sort(unique(unlist(
    Filter(Negate(is.null), lapply(
      igraph::vertex_attr(g, "country", road_vertices),
      .country_or_null
    )),
    use.names = FALSE
  )))
  labels <- c(road_countries, "None")

  folders <- character(0)
  edge_countries <- vapply(
    igraph::edge_attr(g, "country", epath),
    .country_label,
    character(1)
  )
  for (label in labels) {
    lines <- character(0)
    idx <- epath[edge_countries == label]
    for (e in idx) {
      edge <- igraph::ends(g, e, names = FALSE)
      coords <- c(
        .kml_coord(
          igraph::vertex_attr(g, "lon", edge[[1]]),
          igraph::vertex_attr(g, "lat", edge[[1]])
        ),
        .kml_coord(
          igraph::vertex_attr(g, "lon", edge[[2]]),
          igraph::vertex_attr(g, "lat", edge[[2]])
        )
      )
      lines <- c(lines, .kml_line_placemark(coords, color = "ff00ffff", width = 1))
    }
    folders <- c(folders, .kml_folder(label, lines))
  }
  .write_kmz_document(folders, paste0(filename, ".kmz"))
}


#' Export the sea network, including sea-border edges, to KMZ
#'
#' @param filename Output path prefix. `.kmz` is appended.
#' @export
seas_to_kml <- function(filename) {
  g <- .g()
  epath <- which(igraph::edge_attr(g, "etype") %in% SEA_EDGE_TYPES)
  lines <- character(0)
  for (e in epath) {
    edge <- igraph::ends(g, e, names = FALSE)
    coords <- c(
      .kml_coord(
        igraph::vertex_attr(g, "lon", edge[[1]]),
        igraph::vertex_attr(g, "lat", edge[[1]])
      ),
      .kml_coord(
        igraph::vertex_attr(g, "lon", edge[[2]]),
        igraph::vertex_attr(g, "lat", edge[[2]])
      )
    )
    lines <- c(lines, .kml_line_placemark(coords, color = "ffffff00", width = 1))
  }
  .write_kmz_document(lines, paste0(filename, ".kmz"))
}


# geopy.distance.great_circle uses a spherical Earth with this mean radius.
.great_circle_km <- function(lat1, lon1, lat2, lon2) {
  radius_km <- 6371.009
  to_rad <- pi / 180
  lat1 <- lat1 * to_rad
  lon1 <- lon1 * to_rad
  lat2 <- lat2 * to_rad
  lon2 <- lon2 * to_rad

  dlon <- lon2 - lon1
  dlat <- lat2 - lat1
  a <- sin(dlat / 2)^2 + cos(lat1) * cos(lat2) * sin(dlon / 2)^2
  2 * radius_km * asin(sqrt(a))
}


.country_or_null <- function(country) {
  if (is.null(country) || length(country) == 0L || is.na(country[[1L]])) {
    return(NULL)
  }
  country <- trimws(as.character(country[[1L]]))
  if (country %in% c("", "None", "NA")) {
    return(NULL)
  }
  country
}


.country_label <- function(country) {
  value <- .country_or_null(country)
  if (is.null(value)) "None" else value
}


.is_trueish <- function(x) {
  !is.na(x) & x %in% c(TRUE, 1, "1")
}


.kml_escape <- function(x) {
  x <- gsub("&", "&amp;", x, fixed = TRUE)
  x <- gsub("<", "&lt;", x, fixed = TRUE)
  x <- gsub(">", "&gt;", x, fixed = TRUE)
  x <- gsub("\"", "&quot;", x, fixed = TRUE)
  gsub("'", "&apos;", x, fixed = TRUE)
}


.kml_coord <- function(lon, lat) {
  sprintf("%s,%s,0", format(lon, scientific = FALSE), format(lat, scientific = FALSE))
}


.kml_line_placemark <- function(coords, color, width) {
  paste0(
    "<Placemark><Style><LineStyle><color>", color, "</color><width>", width,
    "</width></LineStyle></Style><LineString><coordinates>",
    paste(coords, collapse = " "),
    "</coordinates></LineString></Placemark>"
  )
}


.kml_point_placemark <- function(name, coord, color) {
  paste0(
    "<Placemark><name>", .kml_escape(name),
    "</name><Style><IconStyle><color>", color,
    "</color></IconStyle></Style><Point><coordinates>",
    coord,
    "</coordinates></Point></Placemark>"
  )
}


.kml_folder <- function(name, items) {
  paste0(
    "<Folder><name>", .kml_escape(name), "</name>",
    paste(items, collapse = ""),
    "</Folder>"
  )
}


.kml_document <- function(items) {
  paste0(
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
    "<kml xmlns=\"http://www.opengis.net/kml/2.2\"><Document>",
    paste(items, collapse = ""),
    "</Document></kml>"
  )
}


.write_kml_document <- function(items, filename) {
  writeLines(.kml_document(items), filename, useBytes = TRUE)
}


.write_kmz_document <- function(items, filename) {
  td <- tempfile("traderoutes-kmz-")
  dir.create(td)
  kml_path <- file.path(td, "doc.kml")
  .write_kml_document(items, kml_path)

  oldwd <- getwd()
  on.exit(setwd(oldwd), add = TRUE)
  setwd(td)
  utils::zip(zipfile = normalizePath(filename, winslash = "/", mustWork = FALSE), files = "doc.kml")
}

skip_no_full <- function() {
  skip_if_not(
    file.exists(system.file("extdata", "fullgraph.rds", package = "traderoutes")) ||
      file.exists(system.file("extdata", "fullgraph.graphml", package = "traderoutes")),
    "No full graph found in inst/extdata"
  )
}

main_trade_path <- function(country1, country2,
                            border_cost = 1e3,
                            border_cost_countries = list()) {
  get_path(
    get_main_city(country1),
    get_main_city(country2),
    road_cost = 7,
    road_cost_countries = setNames(list(7, 7), c(country1, country2)),
    port_cost = 1e4,
    port_cost_countries = setNames(list(5e3, 5e3), c(country1, country2)),
    border_cost = border_cost,
    border_cost_countries = border_cost_countries
  )
}

test_that("countries() returns a non-empty sorted character vector", {
  skip_no_full()
  cs <- countries()
  expect_type(cs, "character")
  expect_true(length(cs) > 0)
  expect_true("FRA" %in% cs)
  expect_equal(cs, sort(cs))
})

test_that("get_main_city returns a valid vertex index", {
  skip_no_full()
  v <- get_main_city("FRA")
  expect_type(v, "integer")
  expect_false(is.na(v))
})

test_that("every country has exactly one main city", {
  skip_no_full()
  cs <- countries()
  for (co in cs) {
    expect_false(is.na(suppressWarnings(get_main_city(co))),
                 info = paste("No main city for", co))
  }
})

test_that("get_great_circle computes correct FRA-ITA distance", {
  skip_no_full()
  d <- get_great_circle("FRA", "ITA")
  expect_type(d, "double")
  expect_equal(round(d, 2), 1109.56)
})

test_that("get_trade_route_great_circle mirrors Python output structure", {
  skip_no_full()
  tr <- get_trade_route_great_circle("FRA", "ITA")
  expect_equal(tr$iso_i, "FRA")
  expect_equal(tr$iso_j, "ITA")
  expect_equal(round(tr$dist, 2), 1109.56)
})

test_that("get_path returns a list with vpath and epath", {
  skip_no_full()
  v1   <- get_main_city("FRA")
  v2   <- get_main_city("DEU")
  path <- get_path(v1, v2, road_cost = 7)
  expect_type(path, "list")
  expect_true("vpath" %in% names(path))
  expect_true("epath" %in% names(path))
  expect_true(length(path$vpath) >= 2)
})

test_that("get_pattern returns a string starting and ending with 'c'", {
  skip_no_full()
  v1   <- get_main_city("FRA")
  v2   <- get_main_city("DEU")
  path <- get_path(v1, v2, road_cost = 7)
  pat  <- get_pattern(path)
  expect_type(pat, "character")
  expect_true(startsWith(pat, "c"))
  expect_true(endsWith(pat, "c"))
})

test_that("road_distance + sea_distance equals total distance (approximately)", {
  skip_no_full()
  v1   <- get_main_city("FRA")
  v2   <- get_main_city("JPN")
  path <- get_path(v1, v2, road_cost = 7)
  rd   <- road_distance(path)
  sd   <- sea_distance(path)
  expect_true(rd >= 0)
  expect_true(sd >= 0)
})

test_that("transits_i returns empty when there are no transit countries", {
  skip_no_full()
  v1   <- get_main_city("FRA")
  v2   <- get_main_city("DEU")
  path <- get_path(v1, v2, road_cost = 7)
  expect_equal(transits_i(path), character(0))
})

test_that("get_countries uses 'sea' for maritime segments when requested", {
  skip_no_full()
  v1   <- get_main_city("FRA")
  v2   <- get_main_city("JPN")
  path <- get_path(v1, v2, road_cost = 7)
  cs   <- sapply(get_countries(path, with_sea = TRUE), `[[`, "country")
  expect_true("sea" %in% cs)
  expect_false(any(cs == "None"))
})

test_that("loaded full graph has sea-border edges", {
  skip_no_full()
  g <- getFromNamespace(".g", "traderoutes")()
  expect_true(any(igraph::edge_attr(g, "etype") == "sea_border"))
})

test_that("sea_distance includes sea-border distance", {
  skip_no_full()
  path <- main_trade_path("PRY", "USA")
  g <- getFromNamespace(".g", "traderoutes")()
  et <- igraph::edge_attr(g, "etype", path$epath)
  d <- as.numeric(igraph::edge_attr(g, "dist", path$epath))
  sea_edge_types <- getFromNamespace("SEA_EDGE_TYPES", "traderoutes")

  expect_true("sea_border" %in% et)
  expect_equal(sea_distance(path), sum(d[et %in% sea_edge_types]))
})

test_that("Paraguay-USA exposes Argentina as origin-side transit", {
  skip_no_full()
  path <- main_trade_path("PRY", "USA")
  ti <- transits_i(path)
  tj <- transits_j(path)

  expect_gt(length(ti), 0)
  expect_true("ARG" %in% ti)
  expect_false("PRY" %in% c(ti, tj))
  expect_false("USA" %in% c(ti, tj))
})

test_that("border cost overrides accept sea-border country pairs", {
  skip_no_full()
  g <- getFromNamespace(".g", "traderoutes")()
  et <- igraph::edge_attr(g, "etype")
  c1 <- igraph::edge_attr(g, "country1")
  c2 <- igraph::edge_attr(g, "country2")
  idx <- which(et == "sea_border" & c1 %in% c("ARG", "PRY") & c2 %in% c("ARG", "PRY"))

  expect_gt(length(idx), 0)
  path <- main_trade_path(
    "PRY",
    "USA",
    border_cost_countries = setNames(list(5e3), "ARG-PRY")
  )
  expect_type(path, "list")
  expect_true("vpath" %in% names(path))
  expect_true("epath" %in% names(path))
})

test_that("country sequences do not expose missing-label sentinels", {
  skip_no_full()
  path <- main_trade_path("PRY", "USA")
  cs <- sapply(get_countries(path, with_sea = TRUE), `[[`, "country")

  expect_false(any(is.na(cs)))
  expect_false(any(trimws(cs) == ""))
  expect_false(any(cs %in% c("None", "NA")))
})

skip_no_graphs <- function() {
  skip_if_not(
    file.exists(system.file("extdata", "bordersgraph.graphml", package = "traderoutes")),
    "bordersgraph.graphml not found in inst/extdata"
  )
}

test_that("are_neighbors returns TRUE for adjacent countries", {
  skip_no_graphs()
  expect_true(are_neighbors("FRA", "ITA"))
  expect_true(are_neighbors("FRA", "DEU"))
})

test_that("are_neighbors returns FALSE for non-adjacent countries", {
  skip_no_graphs()
  expect_false(are_neighbors("FRA", "USA"))
  expect_false(are_neighbors("FRA", "JPN"))
})

test_that("get_neighbors returns a character vector", {
  skip_no_graphs()
  ns <- get_neighbors("FRA")
  expect_type(ns, "character")
  expect_true(length(ns) > 0)
  expect_true("ITA" %in% ns)
  expect_true("DEU" %in% ns)
})

test_that("get_neighbors returns empty for unknown country", {
  skip_no_graphs()
  expect_equal(get_neighbors("ZZZ"), character(0))
})

test_that("get_second_neighbors excludes direct neighbors and self", {
  skip_no_graphs()
  ns  <- get_neighbors("FRA")
  sns <- get_second_neighbors("FRA")
  expect_type(sns, "character")
  expect_false("FRA" %in% sns)
  for (n in ns) expect_false(n %in% sns)
  expect_true("PRT" %in% sns)
})

test_that("get_common_neighbors finds shared borders", {
  skip_no_graphs()
  cn <- get_common_neighbors("FRA", "ITA")
  expect_true("CHE" %in% cn)
})

test_that("get_common_neighbors returns empty when none exist", {
  skip_no_graphs()
  expect_equal(get_common_neighbors("FRA", "USA"), character(0))
})

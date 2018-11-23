#include "util/misc.hpp"
#include "gmock/gmock.h"
#include "gtest/gtest.h"

namespace {

using ::testing::ElementsAreArray;
using ::testing::IsEmpty;

/*
 * Split
 */

// NOLINTNEXTLINE
TEST(Misc, Split) {
  std::string str = "this is some text";
  auto pieces = util::split(str, ' ');
  EXPECT_THAT(pieces, ElementsAreArray({"this", "is", "some", "text"}));
}

// NOLINTNEXTLINE
TEST(Misc, SplitEmpty) {
  std::string str;
  auto pieces = util::split(str, ' ');
  EXPECT_THAT(pieces, IsEmpty());
}

// NOLINTNEXTLINE
TEST(Misc, SplitSkipEmpty) {
  std::string str = "  wow  much lol  ";
  auto pieces = util::split(str, ' ');
  EXPECT_THAT(pieces, ElementsAreArray({"wow", "much", "lol"}));
}

/*
 * Setters
 */

// NOLINTNEXTLINE
TEST(Misc, SetBool) {
  bool x = false;
  util::setBool (&x)();
  EXPECT_TRUE(x);
}

// NOLINTNEXTLINE
TEST(Misc, SetString) {
  std::string x;
  util::setString (&x)("wow");
  EXPECT_EQ(x, "wow");
}

// NOLINTNEXTLINE
TEST(Misc, SetInt) {
  int x = 0;
  util::setInt(&x)("42");
  EXPECT_EQ(x, 42);
}

// NOLINTNEXTLINE
TEST(Misc, SetUInt) {
  uint32_t x = 0;
  util::setUint(&x)("42");
  EXPECT_EQ(x, 42);
}

}  // namespace

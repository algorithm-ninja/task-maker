#include "util/union_promise.hpp"
#include <kj/async.h>
#include <kj/debug.h>
#include <bitset>
#include <random>
#include <vector>
#include "gtest/gtest.h"

namespace {

kj::Exception getError(std::string what = "on no!") {
  return kj::Exception(kj::Exception::Type::FAILED, kj::String(), 0,
                       kj::str(what));
}

TEST(UnionPromise, NoPromises) {
  kj::EventLoop loop;
  kj::WaitScope waitScope(loop);

  util::UnionPromiseBuilder builder;

  bool finalized = false;
  std::move(builder)
      .Finalize()
      .then([&]() { finalized = true; })
      .wait(waitScope);
  ASSERT_TRUE(finalized);
}

/*
 * Single Promise fulfilled
 */

TEST(UnionPromise, SinglePromiseFulfilledBeforeAdd) {
  kj::EventLoop loop;
  kj::WaitScope waitScope(loop);

  auto pair = kj::newPromiseAndFulfiller<void>();
  pair.fulfiller->fulfill();

  util::UnionPromiseBuilder builder;
  builder.AddPromise(std::move(pair.promise));
  bool finalized = false;
  std::move(builder)
      .Finalize()
      .then([&]() { finalized = true; })
      .wait(waitScope);
  ASSERT_TRUE(finalized);
}

TEST(UnionPromise, SinglePromiseFulfilledAfterAdd) {
  kj::EventLoop loop;
  kj::WaitScope waitScope(loop);
  util::UnionPromiseBuilder builder;

  auto pair = kj::newPromiseAndFulfiller<void>();
  builder.AddPromise(std::move(pair.promise));
  pair.fulfiller->fulfill();

  bool finalized = false;
  std::move(builder)
      .Finalize()
      .then([&]() { finalized = true; })
      .wait(waitScope);
  ASSERT_TRUE(finalized);
}

TEST(UnionPromise, SinglePromiseFulfilledAfterFinalize) {
  kj::EventLoop loop;
  kj::WaitScope waitScope(loop);
  util::UnionPromiseBuilder builder;
  auto pair = kj::newPromiseAndFulfiller<void>();
  builder.AddPromise(std::move(pair.promise));
  bool finalized = false;
  auto finalizer =
      std::move(builder).Finalize().then([&]() { finalized = true; });
  pair.fulfiller->fulfill();
  finalizer.wait(waitScope);
  ASSERT_TRUE(finalized);
}

/*
 * Single Promise rejected
 */

TEST(UnionPromise, SinglePromisesRejectedBefore) {
  kj::EventLoop loop;
  kj::WaitScope waitScope(loop);

  auto pair = kj::newPromiseAndFulfiller<void>();
  pair.fulfiller->reject(getError());

  util::UnionPromiseBuilder builder;
  builder.AddPromise(std::move(pair.promise));

  bool finalized = false;
  bool errored = false;
  std::move(builder)
      .Finalize()
      .then([&]() { finalized = true; }, [&](auto ex) { errored = true; })
      .wait(waitScope);
  ASSERT_FALSE(finalized);
  ASSERT_TRUE(errored);
}

TEST(UnionPromise, SinglePromisesRejectedAfterAdd) {
  kj::EventLoop loop;
  kj::WaitScope waitScope(loop);

  auto pair = kj::newPromiseAndFulfiller<void>();

  util::UnionPromiseBuilder builder;
  builder.AddPromise(std::move(pair.promise));

  pair.fulfiller->reject(getError());

  bool finalized = false;
  bool errored = false;
  std::move(builder)
      .Finalize()
      .then([&]() { finalized = true; }, [&](auto ex) { errored = true; })
      .wait(waitScope);
  ASSERT_FALSE(finalized);
  ASSERT_TRUE(errored);
}

TEST(UnionPromise, SinglePromisesRejectedAfterFinalize) {
  kj::EventLoop loop;
  kj::WaitScope waitScope(loop);

  auto pair = kj::newPromiseAndFulfiller<void>();

  util::UnionPromiseBuilder builder;
  builder.AddPromise(std::move(pair.promise));

  bool finalized = false;
  bool errored = false;
  auto finalizer = std::move(builder).Finalize().then(
      [&]() { finalized = true; }, [&](auto ex) { errored = true; });

  pair.fulfiller->reject(getError());
  finalizer.wait(waitScope);
  ASSERT_FALSE(finalized);
  ASSERT_TRUE(errored);
}

/*
 * Multiple Promises fulfilled
 */

TEST(UnionPromise, MultiplePromisesFulfilledBeforeAdd) {
  kj::EventLoop loop;
  kj::WaitScope waitScope(loop);

  auto pair1 = kj::newPromiseAndFulfiller<void>();
  auto pair2 = kj::newPromiseAndFulfiller<void>();
  pair1.fulfiller->fulfill();
  pair2.fulfiller->fulfill();

  util::UnionPromiseBuilder builder;
  builder.AddPromise(std::move(pair1.promise));
  builder.AddPromise(std::move(pair2.promise));

  bool finalized = false;
  std::move(builder)
      .Finalize()
      .then([&]() { finalized = true; })
      .wait(waitScope);
  ASSERT_TRUE(finalized);
}

TEST(UnionPromise, MultiplePromisesFulfilledBeforeAndAfterAdd) {
  kj::EventLoop loop;
  kj::WaitScope waitScope(loop);

  auto pair1 = kj::newPromiseAndFulfiller<void>();
  auto pair2 = kj::newPromiseAndFulfiller<void>();
  pair1.fulfiller->fulfill();

  util::UnionPromiseBuilder builder;
  builder.AddPromise(std::move(pair1.promise));
  builder.AddPromise(std::move(pair2.promise));

  pair2.fulfiller->fulfill();

  bool finalized = false;
  std::move(builder)
      .Finalize()
      .then([&]() { finalized = true; })
      .wait(waitScope);
  ASSERT_TRUE(finalized);
}

TEST(UnionPromise, MultiplePromisesFulfilledAfterAdd) {
  kj::EventLoop loop;
  kj::WaitScope waitScope(loop);

  auto pair1 = kj::newPromiseAndFulfiller<void>();
  auto pair2 = kj::newPromiseAndFulfiller<void>();

  util::UnionPromiseBuilder builder;
  builder.AddPromise(std::move(pair1.promise));
  builder.AddPromise(std::move(pair2.promise));

  pair1.fulfiller->fulfill();
  pair2.fulfiller->fulfill();

  bool finalized = false;
  std::move(builder)
      .Finalize()
      .then([&]() { finalized = true; })
      .wait(waitScope);
  ASSERT_TRUE(finalized);
}

TEST(UnionPromise, MultiplePromisesFulfilledAfterFinalize) {
  kj::EventLoop loop;
  kj::WaitScope waitScope(loop);

  auto pair1 = kj::newPromiseAndFulfiller<void>();
  auto pair2 = kj::newPromiseAndFulfiller<void>();
  pair1.fulfiller->fulfill();

  util::UnionPromiseBuilder builder;
  builder.AddPromise(std::move(pair1.promise));
  builder.AddPromise(std::move(pair2.promise));

  bool finalized = false;
  auto finalizer =
      std::move(builder).Finalize().then([&]() { finalized = true; });

  pair2.fulfiller->fulfill();
  finalizer.wait(waitScope);
  ASSERT_TRUE(finalized);
}

/*
 * Multiple Promises rejected
 */

TEST(UnionPromise, MultiplePromisesOneRejectedBeforeAdd) {
  kj::EventLoop loop;
  kj::WaitScope waitScope(loop);

  auto pair1 = kj::newPromiseAndFulfiller<void>();
  auto pair2 = kj::newPromiseAndFulfiller<void>();

  pair1.fulfiller->fulfill();
  pair2.fulfiller->reject(kj::Exception(kj::Exception::Type::FAILED,
                                        kj::heapString(__FILE__), __LINE__,
                                        kj::heapString("Oh no!")));

  util::UnionPromiseBuilder builder;
  builder.AddPromise(std::move(pair1.promise));
  builder.AddPromise(std::move(pair2.promise));

  bool finalized = false;
  bool errored = false;
  std::move(builder)
      .Finalize()
      .then([&]() { finalized = true; }, [&](auto ex) { errored = true; })
      .wait(waitScope);
  ASSERT_FALSE(finalized);
  ASSERT_TRUE(errored);
}

TEST(UnionPromise, MultiplePromisesOneRejectedAfterAdd) {
  kj::EventLoop loop;
  kj::WaitScope waitScope(loop);

  auto pair1 = kj::newPromiseAndFulfiller<void>();
  auto pair2 = kj::newPromiseAndFulfiller<void>();

  pair1.fulfiller->fulfill();

  util::UnionPromiseBuilder builder;
  builder.AddPromise(std::move(pair1.promise));
  builder.AddPromise(std::move(pair2.promise));

  pair2.fulfiller->reject(kj::Exception(kj::Exception::Type::FAILED,
                                        kj::heapString(__FILE__), __LINE__,
                                        kj::heapString("Oh no!")));

  bool finalized = false;
  bool errored = false;
  std::move(builder)
      .Finalize()
      .then([&]() { finalized = true; }, [&](auto ex) { errored = true; })
      .wait(waitScope);
  ASSERT_FALSE(finalized);
  ASSERT_TRUE(errored);
}

TEST(UnionPromise, MultiplePromisesOneRejectedAfterFinalize) {
  kj::EventLoop loop;
  kj::WaitScope waitScope(loop);

  auto pair1 = kj::newPromiseAndFulfiller<void>();
  auto pair2 = kj::newPromiseAndFulfiller<void>();

  pair1.fulfiller->fulfill();

  util::UnionPromiseBuilder builder;
  builder.AddPromise(std::move(pair1.promise));
  builder.AddPromise(std::move(pair2.promise));

  bool finalized = false;
  bool errored = false;
  auto finalizer = std::move(builder).Finalize().then(
      [&]() { finalized = true; }, [&](auto ex) { errored = true; });

  pair2.fulfiller->reject(kj::Exception(kj::Exception::Type::FAILED,
                                        kj::heapString(__FILE__), __LINE__,
                                        kj::heapString("Oh no!")));
  finalizer.wait(waitScope);
  ASSERT_FALSE(finalized);
  ASSERT_TRUE(errored);
}

/*
 * Use cases
 */

TEST(UnionPromise, NonFatalFailures) {
  kj::EventLoop loop;
  kj::WaitScope waitScope(loop);

  bool success = false;
  bool errored = false;
  bool onReadyCalled = false;
  bool onFailureCalled = false;

  util::UnionPromiseBuilder builder(false);
  builder.OnReady([&]() { onReadyCalled = true; });
  builder.OnFailure([&](auto ex) { onFailureCalled = true; });

  auto pair = kj::newPromiseAndFulfiller<void>();
  builder.AddPromise(std::move(pair.promise));
  pair.fulfiller->reject(getError());

  std::move(builder)
      .Finalize()
      .then([&]() { success = true; }, [&](auto ex) { errored = true; })
      .wait(waitScope);
  ASSERT_TRUE(success);
  ASSERT_FALSE(errored);
  ASSERT_TRUE(onReadyCalled);
  ASSERT_FALSE(onFailureCalled);
}

TEST(UnionPromise, RandomResolveOrder) {
  kj::EventLoop loop;
  kj::WaitScope waitScope(loop);

  const int NUM_PROMISES = 10;
  const int SEED = 42;

  std::vector<kj::Promise<void>> promises;
  std::vector<kj::Own<kj::PromiseFulfiller<void>>> fulfillers(NUM_PROMISES);
  for (int i = 0; i < NUM_PROMISES; i++) {
    auto pair = kj::newPromiseAndFulfiller<void>();
    promises.emplace_back(std::move(pair.promise));
    fulfillers[i] = std::move(pair.fulfiller);
  }

  std::mt19937 rnd(SEED);
  std::shuffle(fulfillers.begin(), fulfillers.end(), rnd);

  util::UnionPromiseBuilder builder;
  for (auto&& promise : promises) {
    builder.AddPromise(std::move(promise));
  }
  for (auto&& fulfiller : fulfillers) {
    fulfiller->fulfill();
  }

  bool finalized = false;
  std::move(builder)
      .Finalize()
      .then([&]() { finalized = true; })
      .wait(waitScope);
  ASSERT_TRUE(finalized);
}

TEST(UnionPromise, RandomResolveOrderOneFailed) {
  kj::EventLoop loop;
  kj::WaitScope waitScope(loop);

  const size_t NUM_PROMISES = 100;
  const size_t SEED = 42;

  std::vector<kj::Promise<void>> promises;
  std::vector<kj::Own<kj::PromiseFulfiller<void>>> fulfillers(NUM_PROMISES);
  for (size_t i = 0; i < NUM_PROMISES; i++) {
    auto pair = kj::newPromiseAndFulfiller<void>();
    promises.emplace_back(std::move(pair.promise));
    fulfillers[i] = std::move(pair.fulfiller);
  }

  std::mt19937 rnd(SEED);
  std::shuffle(fulfillers.begin(), fulfillers.end(), rnd);

  util::UnionPromiseBuilder builder;
  for (auto&& promise : promises) {
    builder.AddPromise(std::move(promise));
  }
  size_t failIndex = rnd() % NUM_PROMISES;
  for (size_t i = 0; i < NUM_PROMISES; i++) {
    if (i == failIndex)
      fulfillers[i]->reject(getError());
    else
      fulfillers[i]->fulfill();
  }

  bool finalized = false;
  bool errored = false;
  std::move(builder)
      .Finalize()
      .then([&]() { finalized = true; }, [&](auto ex) { errored = true; })
      .wait(waitScope);
  ASSERT_FALSE(finalized);
  ASSERT_TRUE(errored);
}

TEST(UnionPromise, ChainedPromises) {
  kj::EventLoop loop;
  kj::WaitScope waitScope(loop);

  // A --- B -- D*
  //   \-- C*

  auto A = kj::newPromiseAndFulfiller<void>();
  auto forkedA = A.promise.fork();

  auto B = kj::newPromiseAndFulfiller<void>();
  auto C = kj::newPromiseAndFulfiller<void>();
  auto D = kj::newPromiseAndFulfiller<void>();
  auto tmp1 = forkedA.addBranch()
                  .then([&]() { B.fulfiller->fulfill(); })
                  .eagerlyEvaluate(nullptr);
  auto tmp2 = forkedA.addBranch()
                  .then([&]() { C.fulfiller->fulfill(); })
                  .eagerlyEvaluate(nullptr);
  auto tmp3 = std::move(B.promise)
                  .then([&]() { D.fulfiller->fulfill(); })
                  .eagerlyEvaluate(nullptr);

  util::UnionPromiseBuilder builder;
  builder.AddPromise(std::move(C.promise));
  builder.AddPromise(std::move(D.promise));

  bool finalized = false;
  auto finalizer =
      std::move(builder).Finalize().then([&]() { finalized = true; });
  A.fulfiller->fulfill();
  finalizer.wait(waitScope);
  ASSERT_TRUE(finalized);
}

/*
 * Callback methods
 */

TEST(UnionPromise, OnReady) {
  kj::EventLoop loop;
  kj::WaitScope waitScope(loop);

  util::UnionPromiseBuilder builder;
  const size_t NUM_CALLBACKS = 3;
  std::bitset<NUM_CALLBACKS> done;
  bool errored = false;

  for (size_t i = 0; i < NUM_CALLBACKS; i++) {
    builder.OnReady([&done, i]() { done[i] = true; });
  }
  builder.OnFailure([&errored](auto ex) { errored = true; });

  std::move(builder).Finalize().wait(waitScope);
  ASSERT_TRUE(done.all());
  ASSERT_FALSE(errored);
}

TEST(UnionPromise, OnFailure) {
  kj::EventLoop loop;
  kj::WaitScope waitScope(loop);

  util::UnionPromiseBuilder builder;
  const size_t NUM_CALLBACKS = 3;
  std::bitset<NUM_CALLBACKS> failCallbacks;
  bool succeded = false;

  for (size_t i = 0; i < NUM_CALLBACKS; i++) {
    builder.OnFailure(
        [&failCallbacks, i](auto ex) { failCallbacks[i] = true; });
  }
  builder.OnReady([&succeded]() { succeded = true; });

  auto pair = kj::newPromiseAndFulfiller<void>();
  builder.AddPromise(std::move(pair.promise));
  pair.fulfiller->reject(getError());

  std::move(builder).Finalize().then([]() {}, [](auto ex) {}).wait(waitScope);
  ASSERT_TRUE(failCallbacks.all());
  ASSERT_FALSE(succeded);
}

}  // namespace

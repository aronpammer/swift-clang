// RUN: %clang_cc1 %s -emit-llvm -o - -triple x86_64-darwin-apple -fobjc-arc \
// RUN:   -fexceptions -fcxx-exceptions -O1 | FileCheck %s

// Check that no EH cleanup is emitted around the call to __os_log_helper.
namespace no_eh_cleanup {
  void release(int *lock);

  // CHECK-LABEL: define {{.*}} @_ZN13no_eh_cleanup3logERiPcS1_(
  void log(int &i, char *data, char *buf) {
      int lock __attribute__((cleanup(release)));
      // CHECK: call void @__os_log_helper_1_2_2_4_0_8_34(
      // CHECK-NEXT: call void @_ZN13no_eh_cleanup7releaseEPi
      __builtin_os_log_format(buf, "%d %{public}s", i, data);
  }

  // CHECK: define {{.*}} @__os_log_helper_1_2_2_4_0_8_34({{.*}} [[NUW:#[0-9]+]]
}

// CHECK: attributes [[NUW]] = { {{.*}}nounwind

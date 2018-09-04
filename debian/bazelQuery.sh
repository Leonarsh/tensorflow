# Should probably use [bazel release 0.15.0]]
#
# If Bazel complain "util/hash not found blah blah blah", just remove the
# corresponding line in bazel's BUILD file and try again.
#
# Ref: https://docs.bazel.build/versions/master/query-how-to.html
set -x
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

cat > .bazelrc << EOF
build --action_env PYTHON_BIN_PATH="/usr/bin/python3"
build --action_env PYTHON_LIB_PATH="/usr/lib/python3/dist-packages"
build --python_path="/usr/bin/python3"
build --define with_jemalloc=true
build --define with_gcp_support=true
build --define with_hdfs_support=true
build --define with_aws_support=true
build --define with_kafka_support=true
build:xla --define with_xla_support=true
build:gdr --define with_gdr_support=true
build:verbs --define with_verbs_support=true
build --action_env TF_NEED_OPENCL_SYCL="0"
build --action_env TF_NEED_CUDA="0"
build --action_env TF_DOWNLOAD_CLANG="0"
build --define grpc_no_ares=true
build:opt --copt=-march=native
build:opt --host_copt=-march=native
build:opt --define with_default_optimizations=true
build --strip=always
EOF

# Following queries are arranged in Dependency order.

#
bazel query 'kind("source file", deps(//tensorflow/tools/proto_text:gen_proto_text_functions))' \
	| gawk '{if ($0~/^@/){split($0, sp, "//"); print sp[1];} else {print}}' \
	| sort | uniq \
	> debian/bazelDumps/tf_tool_proto_text.source_file.txt
bazel query 'kind("generated file", deps(//tensorflow/tools/proto_text:gen_proto_text_functions))' \
	| gawk '{if ($0~/^@/){split($0, sp, "//"); print sp[1];} else {print}}' \
	| sort | uniq \
	> debian/bazelDumps/tf_tool_proto_text.generated_file.txt

#
bazel query 'kind("source file", deps(//tensorflow/core:proto_text))' \
	| gawk '{if ($0~/^@/){split($0, sp, "//"); print sp[1];} else {print}}' \
	| sort | uniq \
	> debian/bazelDumps/tf_core_proto_text.source_file.txt
bazel query 'kind("generated file", deps(//tensorflow/core:proto_text))' \
	| gawk '{if ($0~/^@/){split($0, sp, "//"); print sp[1];} else {print}}' \
	| sort | uniq \
	> debian/bazelDumps/tf_core_proto_text.generated_file.txt

#
bazel query 'kind("source file", deps(//tensorflow:libtensorflow_framework.so))' \
	| gawk '{if ($0~/^@/){split($0, sp, "//"); print sp[1];} else {print}}' \
	| grep -E -v 'core.kernels' | grep -E -v 'core.ops' \
	| sort | uniq \
	> debian/bazelDumps/tf_libtensorflow_framework_so.source_file.txt
bazel query 'kind("generated file", deps(//tensorflow:libtensorflow_framework.so))' \
	| gawk '{if ($0~/^@/){split($0, sp, "//"); print sp[1];} else {print}}' \
	| sort | uniq \
	> debian/bazelDumps/tf_libtensorflow_framework_so.generated_file.txt

#
bazel query 'kind("source file", deps(//tensorflow/core:android_tensorflow_lib))' \
	| gawk '{if ($0~/^@/){split($0, sp, "//"); print sp[1];} else {print}}' \
	| sort | uniq \
	> debian/bazelDumps/tf_core_android_tflib.source_file.txt
bazel query 'kind("generated file", deps(//tensorflow/core:android_tensorflow_lib))' \
	| gawk '{if ($0~/^@/){split($0, sp, "//"); print sp[1];} else {print}}' \
	| sort | uniq \
	> debian/bazelDumps/tf_core_android_tflib.generated_file.txt

#
bazel query 'kind("source file", deps(//tensorflow/tools/lib_package:libtensorflow_test))' \
	| gawk '{if ($0~/^@/){split($0, sp, "//"); print sp[1];} else {print}}' \
	| sort | uniq \
	> debian/bazelDumps/tf_libtensorflow_test.source_file.txt
bazel query 'kind("generated file", deps(//tensorflow/tools/lib_package:libtensorflow_test))' \
	| gawk '{if ($0~/^@/){split($0, sp, "//"); print sp[1];} else {print}}' \
	| sort | uniq \
	> debian/bazelDumps/tf_libtensorflow_test.generated_file.txt

#
bazel query 'kind("source file", deps(//tensorflow:libtensorflow.so))' \
	| gawk '{if ($0~/^@/){split($0, sp, "//"); print sp[1];} else {print}}' \
	| sort | uniq \
	> debian/bazelDumps/tf_libtensorflow_so.source_file.txt
bazel query 'kind("generated file", deps(//tensorflow:libtensorflow.so))' \
	| gawk '{if ($0~/^@/){split($0, sp, "//"); print sp[1];} else {print}}' \
	| sort | uniq \
	> debian/bazelDumps/tf_libtensorflow_so.generated_file.txt

#
bazel query 'kind("source file", deps(//tensorflow/python:pywrap_tensorflow))' \
	| gawk '{if ($0~/^@/){split($0, sp, "//"); print sp[1];} else {print}}' \
	| sort | uniq \
	> debian/bazelDumps/tf_python_pywrap_tensorflow.source_file.txt
bazel query 'kind("generated file", deps(//tensorflow/python:pywrap_tensorflow))' \
	| gawk '{if ($0~/^@/){split($0, sp, "//"); print sp[1];} else {print}}' \
	| sort | uniq \
	> debian/bazelDumps/tf_python_pywrap_tensorflow.generated_file.txt

# FIXME
bazel query 'kind(cc_.*, tests(//tensorflow/... -//tensorflow/contrib/... -//tensorflow/python/... -//tensorflow/java/...))' > /dev/null
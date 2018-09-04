#!/usr/bin/python3.6
# Copyright (C) 2018 Mo Zhou <lumin@debian.org>
# Distribution Friendly Light-Weight Build for TensorFlow.
# MIT/Expat License.

'''
Shogun needs the bazel dumps from bazelQuery.sh .

For extra compiler definitions .e.g TENSORFLOW_USE_JEMALLOC please lookup
  tensorflow/core/platform/default/build_config.bzl
'''

from typing import *
import sys
import re
import os
import argparse
import json
import glob
from pprint import pprint
from ninja_syntax import Writer


def ninjaCommonHeader(cursor: Writer, ag: Any) -> None:
    '''
    Writes a common header to the ninja file. ag is parsed arguments.
    '''
    cursor.comment('-- start common ninja header --')
    cursor.comment(f'Note, this ninja file was automatically generated by {__file__}')
    cursor.newline()
    cursor.comment('-- compiling tools --')
    cursor.newline()
    cursor.variable('CXX', 'g++')
    cursor.variable('elf_PROTOC', '/usr/bin/protoc')
    cursor.variable('elf_PROTO_TEXT', f'./proto_text')
    cursor.variable('PROTO_TEXT_ELF', f'./proto_text')
    cursor.comment('SHOGUN_EXTRA is used for adding specific flags for a specific target')
    cursor.variable('SHOGUN_EXTRA', '')
    cursor.newline()
    cursor.comment('-- compiler flags --')
    cursor.newline()
    cursor.variable('CPPFLAGS', '-D_FORTIFY_SOURCE=2 ' + str(os.getenv('CPPFLAGS', '')))
    cursor.variable('CXXFLAGS', '-std=c++14 -O2 -fPIC -gsplit-dwarf'
        + ' -fstack-protector-strong -w ' + str(os.getenv('CXXFLAGS', '')))
    cursor.variable('LDFLAGS', '-Wl,-z,relro ' + str(os.getenv('LDFLAGS', '')))
    cursor.variable('INCLUDES', '-I. -I./debian/embedded/eigen/ -I./third_party/eigen3/'
            + ' -I/usr/include/gemmlowp -I/usr/include/jsoncpp -I/usr/include/llvm-c-7'
            + ' -I/usr/include/llvm-7 -Ithird_party/toolchains/gpus/cuda/')
    cursor.variable('LIBS', '-lpthread -lprotobuf -lnsync -lnsync_cpp -ldouble-conversion'
	+ ' -ldl -lm -lz -lre2 -ljpeg -lpng -lsqlite3 -llmdb -lsnappy -lgif -lLLVM-7')
    cursor.newline()
    cursor.comment('-- compiling rules-- ')
    cursor.rule('rule_PROTOC', f'$elf_PROTOC $in --cpp_out . $SHOGUN_EXTRA')
    cursor.rule('rule_PROTO_TEXT', f'$elf_PROTO_TEXT tensorflow/core tensorflow/core tensorflow/tools/proto_text/placeholder.txt $in')
    cursor.rule('rule_CXX_OBJ', f'$CXX $CPPFLAGS $CXXFLAGS $INCLUDES $SHOGUN_EXTRA -c $in -o $out')
    cursor.rule('rule_CXX_EXEC', f'$CXX $CPPFLAGS $CXXFLAGS $INCLUDES $LDFLAGS $LIBS $SHOGUN_EXTRA $in -o $out')
    cursor.rule('rule_CC_OP_GEN', f'LD_LIBRARY_PATH=. ./$in $out $cc_op_gen_internal tensorflow/core/api_def/base_api')
    cursor.rule('COPY', f'cp $in $out')
    cursor.newline()
    cursor.comment('old rules')
    cursor.rule('PROTOC', f'protoc $in --cpp_out .')
    cursor.rule('PROTOC_GRPC', f'protoc --grpc_out . --cpp_out . --plugin protoc-gen-grpc=/usr/bin/grpc_cpp_plugin $in')
    cursor.rule('PROTO_TEXT', f'$PROTO_TEXT_ELF ./tensorflow/core tensorflow/core tensorflow/tools/proto_text/placeholder.txt $in')
    cursor.rule('GEN_VERSION_INFO', f'bash ./tensorflow/tools/git/gen_git_source.sh $out')
    cursor.rule('CXX_OBJ', f'g++ $CXXFLAGS $INCLUDES -c $in -o $out $CXX_OBJ_EXTRA_DEFS')
    cursor.rule('CXX_EXEC', f'g++ $CXXFLAGS $INCLUDES $LDFLAGS $LIBS $in -o $out')
    cursor.rule('CXX_SHLIB', f'g++ -shared -fPIC $CXXFLAGS $INCLUDES $LDFLAGS $LIBS $in -o $out')
    cursor.rule('STATIC', f'ar rcs $out $in')
    cursor.comment('CXX_CC_OP_EXEC: $in should be e.g. tensorflow/core/ops/array_ops.cc')
    cursor.rule('CXX_CC_OP_EXEC', '$CXX $CPPFLAGS $CXXFLAGS'
            + ' tensorflow/core/framework/op_gen_lib.cc'
            + ' tensorflow/cc/framework/cc_op_gen.cc'
            + ' tensorflow/cc/framework/cc_op_gen_main.cc'
            + ' $in $CC_OP_INC_AND_LIB -o $out')
    cursor.newline()
    cursor.comment('-- end common ninja header --')
    cursor.newline()


def cyan(s: str) -> str:
    return f'\033[1;36m{s}\033[0;m'

def yellow(s: str) -> str:
    return f'\033[1;33m{s}\033[0;m'

def red(s: str) -> str:
    return f'\033[1;31m{s}\033[0;m'


def eGrep(pat: str, sourcelist: List[str]) -> (List[str], List[str]):
    '''
    Just like grep -E
    '''
    match, unmatch = [], []
    for item in sourcelist:
        if re.match(pat, item):
            match.append(item)
        else:
            unmatch.append(item)
    return match, unmatch


def bazelPreprocess(srclist: List[str]) -> List[str]:
    '''
    1. Filter out external dependencies from bazel dependency dump.
    2. Mangle file path.
    3. Report the depending libraries.
    '''
    deplist, retlist = set([]), []
    for src in srclist:
        if re.match('^@(\w*).*', src):
            # It's an external dependency
            deplist.update(re.match('^@(\w*).*', src).groups())
        elif re.match('^..third_party.*', src):
            pass # ignore
        else:
            # it's an tensorflow source
            retlist.append(re.sub('^//', '', re.sub(':', '/', src)))
    print(cyan('Required Depends:'), list(deplist))
    print('Globbed', cyan(f'{len(srclist)}'), 'source files')
    return retlist


#def ninjaProto(cur, protolist: List[str]) -> List[str]:
#    '''
#    write ninja rules for the protofiles. cur is ninja writer
#    '''
#    protos, cclist, hdrlist = [], [], []
#    for proto in protolist:
#        # proto is a protobuf-related file.
#        if proto.endswith('.proto'):
#            protos.append(proto)
#            cclist.append(re.sub('.proto$', '.pb.cc', proto))
#            hdrlist.append(re.sub('.proto$', '.pb.h', proto))
#        elif proto.endswith('.pb.cc'):
#            protos.append(re.sub('.pb.cc$', '.proto', proto))
#            cclist.append(proto)
#            hdrlist.append(re.sub('.pb.cc$', '.pb.h', proto))
#        elif proto.endswith('.pb.h'):
#            protos.append(re.sub('.pb.h$', '.proto', proto))
#            cclist.append(re.sub('.pb.h$', '.pb.cc', proto))
#            hdrlist.append(proto)
#        else:
#            raise SyntaxError(f'what is {proto}?')
#    for p in list(set(protos)):
#        output = [re.sub('.proto$', '.pb.cc', p),
#                re.sub('.proto$', '.pb.h', p)]
#        cur.build(output, 'PROTOC', inputs=p)
#    return list(set(protos)), list(set(cclist)), list(set(hdrlist))
#
#
#def ninjaProtoText(cur, protolist: List[str]) -> List[str]:
#    '''
#    write ninja rules for to proto_text files. cur is ninja writer
#    '''
#    protos, cclist, hdrlist = [], [], []
#    for proto in protolist:
#        # proto is a proto_text-related file
#        if proto.endswith('.proto'):
#            protos.append(proto)
#            cclist.append(re.sub('.proto$', '.pb_text.cc', proto))
#            hdrlist.append(re.sub('.proto$', '.pb_text.h', proto))
#            hdrlist.append(re.sub('.proto$', '.pb_text-impl.h', proto))
#        elif proto.endswith('.pb_text.cc'):
#            protos.append(re.sub('.pb_text.cc$', '.proto', proto))
#            cclist.append(proto)
#            hdrlist.append(re.sub('.pb_text.cc$', '.pb_text.h', proto))
#            hdrlist.append(re.sub('.pb_text.cc$', '.pb_text-impl.h', proto))
#        elif proto.endswith('.pb_text.h'):
#            protos.append(re.sub('.pb_text.h$', '.proto', proto))
#            cclist.append(re.sub('.pb_text.h$', '.pb_text.cc', proto))
#            hdrlist.append(proto)
#            hdrlist.append(re.sub('.pb_text.h$', '.pb_text-impl.h', proto))
#        elif proto.endswith('.pb_text-impl.h'):
#            protos.append(re.sub('.pb_text-impl.h$', '.proto', proto))
#            cclist.append(re.sub('.pb_text-impl.h$', '.pb_text.cc', proto))
#            hdrlist.append(re.sub('.pb_text-impl.h$', '.pb_text.h', proto))
#            hdrlist.append(proto)
#        else:
#            raise SyntaxError(f'what is {proto}?')
#    for p in list(set(protos)):
#        output = [re.sub('.proto$', '.pb_text.cc', p),
#                re.sub('.proto$', '.pb_text.h', p),
#                re.sub('.proto$', '.pb_text-impl.h', p)]
#        cur.build(output, 'PROTO_TEXT', inputs=p)
#    return list(set(protos)), list(set(cclist)), list(set(hdrlist))
#
#
#def ninjaCXXOBJ(cur, cclist: List[str]) -> List[str]:
#    '''
#    write ninja rules for building .cc files into object files
#    '''
#    objs = []
#    exception_eigen_avoid_std_array = [
#        'sparse_tensor_dense_matmul_op', 'conv_grad_ops_3d',
#        'adjust_contrast_op' ]
#    for cc in cclist:
#        output = re.sub('.cc$', '.o', cc)
#        if any(x in cc for x in exception_eigen_avoid_std_array):
#            objs.append(cur.build(output, 'CXX_OBJ', inputs=cc,
#                variables={'CXX_OBJ_EXTRA_DEFS': '-DEIGEN_AVOID_STL_ARRAY'})[0])
#        else:
#            objs.append(cur.build(output, 'CXX_OBJ', inputs=cc)[0])
#    return objs


def shogunAllProto(argv):
    '''
    Generate XXX.pb.{h,cc} files from all available XXX.proto
    files in the source directory.

    Depends: protoc (protobuf-compiler)
    Input: .proto
    Output: .pb.cc, .pb.h
    '''
    ag = argparse.ArgumentParser()
    ag.add_argument('-o', help='write ninja file', type=str, default='all_proto.ninja')
    ag = ag.parse_args(argv)
    print(red(f'{ag}'))

    # (1) initialize ninja file
    cursor = Writer(open(ag.o, 'w'))
    ninjaCommonHeader(cursor, ag)

    # (2) glob all proto
    protos = glob.glob(f'**/*.proto', recursive=True)
    print(cyan('AllProto:'), f'globbed {len(protos)} .proto files')

    # (3) generate .pb.cc, .pb.h
    for proto in protos:
        cursor.build([ proto.replace('.proto', '.pb.cc'),
            proto.replace('.proto', '.pb.h')], 'rule_PROTOC', proto)

    # done
    cursor.close()


def shogunProtoText(argv):
    '''
    Build a binary ELF executable named proto_text, which generates
    XXX.pb_text{.cc,.h,-impl.h} files from a given XXX.proto file.
    This binary file is for one-time use.

    Depends: shogunAllProto
    Input: bazelDump, cxx source
    Output: proto_text
    '''
    ag = argparse.ArgumentParser()
    ag.add_argument('-i', help='list of source files', type=str, required=True)
    ag.add_argument('-g', help='list of generated files', type=str, required=True)
    ag.add_argument('-o', help='where to write the ninja file', type=str, default='proto_text.ninja')
    ag = ag.parse_args(argv)
    print(red(f'{ag}'))

    srclist = bazelPreprocess([l.strip() for l in open(ag.i, 'r').readlines()])
    genlist = bazelPreprocess([l.strip() for l in open(ag.g, 'r').readlines()])

    # (1) Instantiate ninja writer
    cursor = Writer(open(ag.o, 'w'))
    ninjaCommonHeader(cursor, ag)

    # (2) deal with generated files
    # (2.1) .pb.cc and .pb.h files are generated in shogunAllProto
    _, genlist = eGrep('.*.pb.h$', genlist)
    pbcclist, genlist = eGrep('.*.pb.cc$', genlist)
    if len(genlist) > 0:
        print(yellow('Remainders:'), genlist)

    # (3) deal with source files
    # (3.1) filter-out not needed files
    _, srclist = eGrep('.*.h$', srclist) # we don't need to deal with header here
    _, srclist = eGrep('^third_party', srclist) # no third_party stuff
    _, srclist = eGrep('.*windows/.*', srclist) # no windoge source
    _, srclist = eGrep('.*.proto$', srclist) # already dealt with in (2)

    # (3.2) compile .cc source
    cclist, srclist = eGrep('.*.cc', srclist)
    objlist = []
    for cc in cclist + pbcclist:
        obj = cc.replace('.cc', '.o')
        objlist.append(cursor.build(obj, 'rule_CXX_OBJ', cc)[0])
    if len(srclist) > 0:
        print(yellow('Remainders:'), srclist)

    # (4) link objects into the final ELF
    cursor.build(f'proto_text', 'rule_CXX_EXEC', inputs=objlist,
            variables={'LIBS': '-lpthread -lprotobuf -ldouble-conversion'})

    # done
    cursor.close()


def shogunTFLib_framework(argv):
    '''
    Build libtensorflow_framework.so. With slight modification, this
    function should be able to build libtensorflow_android.so too.

    Depends: AllProto, proto_text
    Input: bazelDump, cxx source
    Output: libtensorflow_framework.so
    '''
    ag = argparse.ArgumentParser()
    ag.add_argument('-i', help='list of source files', type=str, required=True)
    ag.add_argument('-g', help='list of generated files', type=str, required=True)
    ag.add_argument('-o', help='where to write the ninja file', type=str, default='libtensorflow_framework.ninja')
    ag = ag.parse_args(argv)
    print(red(f'{ag}'))

    srclist = bazelPreprocess([l.strip() for l in open(ag.i, 'r').readlines()])
    genlist = bazelPreprocess([l.strip() for l in open(ag.g, 'r').readlines()])

    # (1) Initialize ninja file
    cursor = Writer(open(ag.o, 'w'))
    ninjaCommonHeader(cursor, ag)

    # (2) deal with generated files
    # (2.1) .pb.h and .pb.cc are already generated by shogunAllProto
    gen_pbh, genlist = eGrep('.*.pb.h', genlist)
    gen_pbcc, genlist = eGrep('.*.pb.cc', genlist)

    # (2.2) .pb_text.*
    pbtlist = [x for x in genlist if any(x.endswith(y) for y in ('.pb_text.h', '.pb_text.cc', '.pb_text-impl.h'))]
    pbtlist = [x.replace('.pb_text.h', '.proto').replace('.pb_text.cc', '.proto').replace('.pb_text-impl.h', '.proto') for x in pbtlist]
    gen_pbth, genlist = eGrep('.*.pb_text.h', genlist)
    gen_pbtih, genlist = eGrep('.*.pb_text-impl.h', genlist)
    gen_pbtcc, genlist = eGrep('.*.pb_text.cc', genlist)
    for pbt in list(set(pbtlist)):
        cursor.build([
            pbt.replace('.proto', '.pb_text.h'),
            pbt.replace('.proto', '.pb_text.cc'),
            pbt.replace('.proto', '.pb_text-impl.h')
            ], 'rule_PROTO_TEXT', pbt)
    if genlist:
        print(yellow('Remainders:'), genlist)
        assert(len(genlist) == 1)

    # (3) deal with source files
    # (3.1) filter-out files from list
    _, srclist = eGrep('.*.proto$', srclist) # done in (2)
    src_hdrs, srclist = eGrep('.*.h$', srclist)
    _, srclist = eGrep('^third_party', srclist)
    _, srclist = eGrep('.*/windows/.*', srclist) # no windoge source.

    # (3.2) compile .cc source
    src_cc, srclist = eGrep('.*.cc', srclist)
    objlist = []
    for cc in src_cc + gen_pbcc + gen_pbtcc + genlist:
        variables = {}
        if any(x in cc for x in ('posix/port.cc',)):
            variables = {'SHOGUN_EXTRA': '-DTENSORFLOW_USE_JEMALLOC'}
        obj = cursor.build(cc.replace('.cc', '.o'), 'rule_CXX_OBJ', inputs=cc, variables=variables)[0]
        objlist.append(obj)

    # (4) link the final executable
    cursor.build('libtensorflow_framework.so', 'CXX_SHLIB', inputs=objlist,
            variables={'LIBS': '-lfarmhash -lhighwayhash -lsnappy -lgif'
            + ' -ldouble-conversion -lz -lprotobuf -ljpeg -lnsync -lnsync_cpp'
            + ' -lpthread -ljemalloc'})

    # done
    cursor.close()


def shogunCCOP(argv):
    '''
    Generate tensorflow cc ops : tensorflow/cc/ops/*.cc and *.h

    Depends: AllProto, proto_text, libtensorflow_framework
    Input: cc source, bazel dump
    Output: one-time-use binary "XXX_gen_cc" and generated .cc .h files.
    '''
    ag = argparse.ArgumentParser()
    ag.add_argument('-i', help='list of source files', type=str, required=True)
    ag.add_argument('-g', help='list of generated files', type=str, required=True)
    ag.add_argument('-o', help='where to write the ninja file', type=str, default='ccop.ninja')
    ag = ag.parse_args(argv)
    print(red(f'{ag}'))

    genlist = bazelPreprocess([l.strip() for l in open(ag.g, 'r').readlines()])

    # (1) Instantiate ninja writer
    cursor = Writer(open(ag.o, 'w'))
    ninjaCommonHeader(cursor, ag)

    # (2) filter unrelated files, we only want cc_op related files.
    _, genlist = eGrep('.*.pb.h', genlist)
    _, genlist = eGrep('.*.pb.cc', genlist)
    _, genlist = eGrep('.*.pb_text.h', genlist)
    _, genlist = eGrep('.*.pb_text-impl.h', genlist)
    _, genlist = eGrep('.*.pb_text.cc', genlist)

    # (3) XXX_gen_cc
    # (3.1) deal with a missing source
    cursor.build('tensorflow/core/ops/user_ops.cc', 'COPY', inputs='tensorflow/core/user_ops/fact.cc')

    # (3.2) build several common objects
    main_cc = ['tensorflow/core/framework/op_gen_lib.cc',
        'tensorflow/cc/framework/cc_op_gen.cc',
        'tensorflow/cc/framework/cc_op_gen_main.cc',
        ]
    main_obj = [x.replace('.cc', '.o') for x in main_cc]
    for cc in main_cc:
        cursor.build(cc.replace('.cc', '.o'), 'rule_CXX_OBJ', inputs=cc)

    # (3.2) build executables and generate file with executable
    gen_ccopcc, genlist = eGrep('.*/cc/ops/.*.cc', genlist)
    gen_ccoph, genlist = eGrep('.*/cc/ops/.*.h', genlist)
    opnamelist = list(set(os.path.basename(x.replace('.cc', '').replace('.h', ''))
        for x in (gen_ccopcc + gen_ccoph) if 'internal' not in x ))

    for opname in opnamelist:
        coreopcc = 'tensorflow/core/ops/' + opname + '.cc'
        ccopcc   = 'tensorflow/cc/ops/'   + opname + '.cc'

        # build corresponding elf executable
        cursor.build(f'{opname}_gen_cc', 'rule_CXX_EXEC', inputs=[coreopcc] + main_obj,
            variables={'SHOGUN_EXTRA': '-I. -L. -ltensorflow_framework'})

        # generate file
        cursor.build([ccopcc.replace('.cc', '.h'), ccopcc], 'rule_CC_OP_GEN', inputs=f'{opname}_gen_cc',
                variables={'cc_op_gen_internal': '0' if opname != 'sendrecv_ops' else '1'},
                implicit_outputs=[ccopcc.replace('.cc', '_internal.h'), ccopcc.replace('.cc', '_internal.cc')])

    ## done
    cursor.close()


def shogunTFLib(argv):
    '''
    Build libtensorflow.so
    '''
    ag = argparse.ArgumentParser()
    ag.add_argument('-i', help='list of source files', type=str, required=True)
    ag.add_argument('-g', help='list of generated files', type=str, required=True)
    ag.add_argument('-o', help='where to write the ninja file', type=str,
            default='libtensorflow.ninja')
    ag.add_argument('-B', help='build directory', type=str, default='.')
    ag = ag.parse_args(argv)

    srclist = filteroutExternal([l.strip() for l in open(ag.i, 'r').readlines()])
    genlist = filteroutExternal([l.strip() for l in open(ag.g, 'r').readlines()])
    srclist, genlist = mangleBazel(srclist), mangleBazel(genlist)

    # Instantiate ninja writer
    cursor = Writer(open(ag.o, 'w'))
    ninjaCommonHeader(cursor, ag)

    # generate .pb.cc and .pb.h
    srcproto, srclist = eGrep('.*.proto$', srclist)
    genpbh, genlist = eGrep('.*.pb.h', genlist)
    genpbcc, genlist = eGrep('.*.pb.cc', genlist)
    protolist, pbcclist, pbhlist = ninjaProto(cursor,
            [x for x in (genpbh + genpbcc) if '.grpc.pb' not in x])
    proto_diff = set(srcproto).difference(set(protolist))
    if len(proto_diff) > 0:
        print(yellow('Warning: resulting proto lists different!'), proto_diff)

    # generate .pb_text.cc .pb_text.h .pb_test-impl.h
    genpbth, genlist = eGrep('.*.pb_text.h', genlist)
    genpbtimplh, genlist = eGrep('.*.pb_text-impl.h', genlist)
    genpbtcc, genlist = eGrep('.*.pb_text.cc', genlist)
    pbtprotolist, pbtcclist, pbthlist = ninjaProtoText(cursor,
            genpbth + genpbtimplh + genpbtcc)
    pbtproto_diff = set(srcproto).difference(set(pbtprotolist))
    if len(proto_diff) > 0:
        print(yellow('Warning: resulting proto lists different!'), proto_diff)

    # XXX: temporary workaround for //tensorflow/core/debug:debug_service.grpc.pb.cc
    cursor.build([f'{ag.B}/tensorflow/core/debug/debug_service.grpc.pb.cc',
        f'{ag.B}/tensorflow/core/debug/debug_service.grpc.pb.h'],
        'PROTOC_GRPC', inputs='tensorflow/core/debug/debug_service.proto')
    pbcclist.append(f'{ag.B}/tensorflow/core/debug/debug_service.grpc.pb.cc')

    # ignore .h files and third_party, and windows source
    _, srclist = eGrep('.*.h$', srclist)
    _, srclist = eGrep('^third_party', srclist)
    _, srclist = eGrep('.*windows/env_time.cc$', srclist)
    _, srclist = eGrep('.*platform/windows.*', srclist)
    _, srclist = eGrep('.*.cu.cc$', srclist) # no CUDA file for CPU-only build
    _, srclist = eGrep('.*.pbtxt$', srclist) # no need to process
    _, srclist = eGrep('.*platform/cloud.*', srclist) # SSL 1.1.1 broke this.
    _, srclist = eGrep('.*platform/s3.*', srclist) # we don't have https://github.com/aws/aws-sdk-cpp
    _, srclist = eGrep('.*_main.cc$', srclist) # don'e include any main function.
    _, srclist = eGrep('.*cc_op_gen_main.cc$', srclist) # don't include main function.

    # cc_op_gen
    ccoplist, genlist = eGrep('.*/cc/ops/.*.cc', genlist)
    ccophdrs, genlist = eGrep('.*/cc/ops/.*.h', genlist)

    # compile .cc source
    cclist, srclist = eGrep('.*.cc', srclist)
    tf_android_objs = ninjaCXXOBJ(cursor, cclist + pbcclist + pbtcclist + ccoplist)

    # link the final executable
    cursor.build('libtensorflow.so', 'CXX_SHLIB', inputs=tf_android_objs,
            variables={'LIBS': '-lpthread -lprotobuf -lnsync -lnsync_cpp'
                + ' -ldouble-conversion -lz -lpng -lgif -lhighwayhash'
                + ' -ljpeg -lfarmhash -ljsoncpp -lsqlite3 -lre2 -lcurl'
                + ' -llmdb -lsnappy'})
    # FIXME: jemalloc, mkl-dnn, grpc, xsmm

    ## fflush
    print(yellow('Unprocessed src files:'), json.dumps(srclist, indent=4))
    print(yellow('Unprocessed gen files:'), json.dumps(genlist, indent=4))
    cursor.close()


if __name__ == '__main__':

    # A graceful argparse implementation with argparse subparser requries
    # much more boring code than I would like to write.
    try:
        sys.argv[1]
    except IndexError as e:
        print(e, 'you must specify one of the following a subcommand:')
        print([k for (k, v) in locals().items() if k.startswith('shogun')])
        exit(1)

    # Targets sorted in dependency order.
    if sys.argv[1] in ('AllProto', 'ProtoText', 'TFLib_framework', 'CCOP'):
        eval(f'shogun{sys.argv[1]}')(sys.argv[2:])
    elif sys.argv[1] == 'TFLib':
        shogunTFLib(sys.argv[2:])
    else:
        raise NotImplementedError(sys.argv[1:])

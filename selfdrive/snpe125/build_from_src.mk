CC = clang
CXX = clang++

BASEDIR = ../..
EXTERNAL = ../../external
PHONELIBS = ../../phonelibs

WARN_FLAGS = -Werror=implicit-function-declaration \
             -Werror=incompatible-pointer-types \
             -Werror=int-conversion \
             -Werror=return-type \
             -Werror=format-extra-args \
             -Wno-deprecated-declarations

CFLAGS = -std=gnu11 -fPIC -O2 $(WARN_FLAGS)
CXXFLAGS = -std=c++14 -fPIC -O2 $(WARN_FLAGS)

#ifneq ($(RELEASE),1)
#CFLAGS += -g
#CXXFLAGS += -g
#endif

JSON_FLAGS = -I$(PHONELIBS)/json/src
JSON11_FLAGS = -I$(PHONELIBS)/json11/
EIGEN_FLAGS = -I$(PHONELIBS)/eigen

UNAME_M := $(shell uname -m)
UNAME_S := $(shell uname -s)

ifeq ($(UNAME_M),x86_64)

ifeq ($(UNAME_S),Darwin)
  LIBYUV_FLAGS = -I$(PHONELIBS)/libyuv/include
  LIBYUV_LIBS = $(PHONELIBS)/libyuv/mac/lib/libyuv.a

  ZMQ_FLAGS = -I$(EXTERNAL)/zmq/include
  ZMQ_LIBS = $(PHONELIBS)/zmq/mac/lib/libczmq.a \
             $(PHONELIBS)/zmq/mac/lib/libzmq.a

  OPENCL_LIBS = -framework OpenCL
else
  LIBYUV_FLAGS = -I$(PHONELIBS)/libyuv/x64/include
  LIBYUV_LIBS = $(PHONELIBS)/libyuv/x64/lib/libyuv.a

  ZMQ_FLAGS = -I$(EXTERNAL)/zmq/include
  ZMQ_LIBS = -L$(EXTERNAL)/zmq/lib \
             -l:libczmq.a -l:libzmq.a

  OPENCL_LIBS = -lOpenCL
endif

  CURL_FLAGS = -I/usr/include/curl
  CURL_LIBS = -lcurl -lz

  SSL_FLAGS = -I/usr/include/openssl/
  SSL_LIBS = -lssl -lcrypto

  OPENCV_FLAGS =
  OPENCV_LIBS = -lopencv_video \
                -lopencv_imgproc \
                -lopencv_core \
                -lopencv_highgui
  OTHER_LIBS = -lz -lm -lpthread

  PLATFORM_OBJS = camera_fake.o \
                  ../common/visionbuf_cl.o

  CFLAGS += -D_GNU_SOURCE \
            -DCLU_NO_CACHE
else
	# assume phone

  LIBYUV_FLAGS = -I$(PHONELIBS)/libyuv/include
  LIBYUV_LIBS = $(PHONELIBS)/libyuv/lib/libyuv.a

  ZMQ_FLAGS = -I$(PHONELIBS)/zmq/aarch64/include
  ZMQ_LIBS = -L$(PHONELIBS)/zmq/aarch64/lib \
             -l:libczmq.a -l:libzmq.a \
             -lgnustl_shared

  CURL_FLAGS = -I$(PHONELIBS)/curl/include
  CURL_LIBS = $(PHONELIBS)/curl/lib/libcurl.a \
              $(PHONELIBS)/zlib/lib/libz.a

  SSL_FLAGS = -I$(PHONELIBS)/boringssl/include
  SSL_LIBS = $(PHONELIBS)/boringssl/lib/libssl_static.a \
             $(PHONELIBS)/boringssl/lib/libcrypto_static.a

  OPENCL_FLAGS = -I$(PHONELIBS)/opencl/include
  OPENCL_LIBS = -lgsl -lCB -lOpenCL

  OPENCV_FLAGS = -I/usr/local/sdk/native/jni/include
  OPENCV_LIBS = -L/usr/local/sdk/native/libs \
                -l:libopencv_video.a \
                -l:libopencv_imgproc.a \
                -l:libopencv_core.a

  OPENGL_LIBS = -lGLESv3 -lEGL

  SNPE_FLAGS = -I$(PHONELIBS)/snpe/include/
  SNPE_LIBS = -lSNPE -lsymphony-cpu -lsymphonypower

  OTHER_LIBS = -lz -lcutils -lm -llog -lui -ladreno_utils

  PLATFORM_OBJS = camera_qcom.o \
                  ../common/visionbuf_ion.o

  CFLAGS += -DQCOM
  CXXFLAGS += -DQCOM
endif

OBJS = main.o
OUTPUT = main.so

.PHONY: all
all: $(OUTPUT)

include ../common/cereal.mk

#MODEL_DATA = ../../models/driving_bigmodel.dlc ../../models/monitoring_model.dlc ../../models/posenet.dlc

MODEL_DATA = ../../models/driving_model.dlc ../../models/monitoring_model.dlc ../../models/posenet.dlc
MODEL_OBJS = $(MODEL_DATA:.dlc=.o)

ifeq ($(RELEASE),1)
CFLAGS += -DCLU_NO_SRC
CXXFLAGS += -DCLU_NO_SRC
CLCACHE_FILES = $(wildcard /tmp/clcache/*.clb)
CLCACHE_OBJS += $(CLCACHE_FILES:.clb=.o)
OBJS += $(CLCACHE_OBJS)

clutil.o: clcache_bins.h
clcache_bins.h: $(CLCACHE_FILES) /tmp/clcache/index.cli
	rm -f '$@'
	for hash in $(basename $(notdir $(CLCACHE_FILES))) ; do \
		echo "extern const uint8_t clb_$$hash[] asm(\"_binary_$${hash}_clb_start\");" ; \
		echo "extern const uint8_t clb_$${hash}_end[] asm(\"_binary_$${hash}_clb_end\");" ; \
	done >> '$@'
	echo "static const CLUProgramIndex clu_index[] = {" >> '$@'
	while read idx_hash code_hash; do \
		echo "{ 0x$$idx_hash, clb_$${code_hash}, clb_$${code_hash}_end }," ; \
	done < /tmp/clcache/index.cli >> '$@'
	echo "};" >> '$@'

$(CLCACHE_OBJS): %.o: %.clb
	@echo "[ bin2o ] $@"
	cd '$(dir $<)' && ld -r -b binary '$(notdir $<)' -o '$(abspath $@)'


endif

DEPS := $(OBJS:.o=.d)

.PHONY: all

LDFLAGS= -shared

$(OUTPUT): $(OBJS)
	@echo "[ LINK ] $@"
	$(CXX) -fPIC -o '$@' $^ -shared \
        $(SNPE_LIBS) \


%.o: %.cc
	@echo "[ CXX ] $@"
	$(CXX) $(CXXFLAGS) -MMD \
           -Iinclude -I.. -I../.. \
           $(SNPE_FLAGS) \
           -c -o '$@' '$<'



main1.so: $(OBJS)
	$(CXX) -shared -o '$@' $^ -lm



.PHONY: clean
clean:
	rm -f $(OBJS) $(DEPS)

-include $(DEPS)

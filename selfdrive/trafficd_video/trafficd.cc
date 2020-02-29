#include "traffic.h"

using namespace std;

std::unique_ptr<zdl::SNPE::SNPE> snpe;
volatile sig_atomic_t do_exit = 0;

const std::vector<std::string> modelLabels = {"RED", "GREEN", "YELLOW", "NONE"};
const double modelRate = 1 / 5.;  // 5 Hz

const int image_stride = 3840;  // global constants
const int original_shape[3] = {874, 1164, 3};
const int original_size = 874 * 1164 * 3;
const int cropped_shape[3] = {515, 814, 3};
const int cropped_size = 515 * 814 * 3;

const float pixel_norm = 255.0;
const int horizontal_crop = 175;
const int top_crop = 0;
const int hood_crop = 209;
const int offset = horizontal_crop * cropped_shape[2];
const double msToSec = 1 / 1000.;  // multiply
const double secToUs = 1e+6;

zdl::DlSystem::Runtime_t checkRuntime() {
    static zdl::DlSystem::Version_t Version = zdl::SNPE::SNPEFactory::getLibraryVersion();
    static zdl::DlSystem::Runtime_t Runtime;
    std::cout << "SNPE Version: " << Version.asString().c_str() << std::endl; //Print Version number
    if (zdl::SNPE::SNPEFactory::isRuntimeAvailable(zdl::DlSystem::Runtime_t::GPU)) {
        Runtime = zdl::DlSystem::Runtime_t::GPU;
    } else {
        Runtime = zdl::DlSystem::Runtime_t::CPU;
    }
    return Runtime;
}

void initializeSNPE(zdl::DlSystem::Runtime_t runtime) {
    std::unique_ptr<zdl::DlContainer::IDlContainer> container;
    container = zdl::DlContainer::IDlContainer::open("../../models/video_test.dlc");
    zdl::SNPE::SNPEBuilder snpeBuilder(container.get());
    snpe = snpeBuilder.setOutputLayers({})
                      .setRuntimeProcessor(runtime)
                      .setUseUserSuppliedBuffers(true)
                      .setPerformanceProfile(zdl::DlSystem::PerformanceProfile_t::HIGH_PERFORMANCE)
                      .setCPUFallbackMode(true)
                      .build();
}

void createUserBuffer(){
    zdl::DlSystem::UserBufferMap inputMap;
    std::unique_ptr<zdl::DlSystem::IUserBuffer> inputBuffer;
    std::unique_ptr<zdl::DlSystem::IUserBuffer> outputBuffer;

    zdl::DlSystem::IUserBufferFactory& ubFactory = zdl::SNPE::SNPEFactory::getUserBufferFactory();
    zdl::DlSystem::UserBufferEncodingFloat userBufferEncodingFloat;
    const auto &strListi_opt = snpe->getInputTensorNames();
    if (!strListi_opt) throw std::runtime_error("Error obtaining Input tensor names");
    const auto &strListi = *strListi_opt;
    //assert(strListi.size() == 1);
    const char *input_tensor_name = strListi.at(0);

    const auto &strListo_opt = snpe->getOutputTensorNames();
    if (!strListo_opt) throw std::runtime_error("Error obtaining Output tensor names");
    const auto &strListo = *strListo_opt;
    assert(strListo.size() == 1);
    const char *output_tensor_name = strListo.at(0);

    const auto &inputDims_opt = snpe->getInputDimensions(input_tensor_name);
    const zdl::DlSystem::TensorShape& bufferShape = *inputDims_opt;
    std::vector<size_t> strides(bufferShape.rank());
    strides[strides.size() - 1] = sizeof(float);
    size_t product = 1;
    for (size_t i = 0; i < bufferShape.rank(); i++) product *= bufferShape[i];
    size_t stride = strides[strides.size() - 1];
    for (size_t i = bufferShape.rank() - 1; i > 0; i--) {
      stride *= bufferShape[i];
      strides[i-1] = stride;
    }
    std::cout << "input product is " << product << "\n";
    inputBuffer = ubFactory.createUserBuffer(NULL, product*sizeof(float), strides, &userBufferEncodingFloat);
    inputMap.add(input_tensor_name, inputBuffer.get());

    std::vector<float> images;
    float *inputImages = new float[15260040];
    ifstream infile("/data/openpilot/selfdrive/trafficd_video/images/video");
    string line;

    if (infile.is_open()){
        int idx = 0;
        while(infile.good()){
            getline(infile, line);
            inputImages[idx] = stoi(line) / 255.0;
            // images.push_back(stoi(line) / 255.0);
            idx++;
        }
    }
    infile.close();
    zdl::DlSystem::UserBufferMap outputMap;

    size_t output_size = 4;
    float* output;
    std::vector<size_t> outputStrides = {output_size * sizeof(float), sizeof(float)};
    outputBuffer = ubFactory.createUserBuffer(output, output_size * sizeof(float), outputStrides, &userBufferEncodingFloat);
    outputMap.add(output_tensor_name, outputBuffer.get());

    assert(inputBuffer->setBufferAddress(inputImages));
    snpe->execute(inputMap, outputMap);
    for (int i=0; i < 4; i++){
        std::cout << output[i] << std::endl;
    }
    for (int i=0; i < 4; i++){
        std::cout << outputBuffer[i] << std::endl;
    }
    for (int i=0; i < 4; i++){
        std::cout << outputMap[i] << std::endl;
    }

//    const zdl::DlSystem::StringList& outputBufferNames = outputMap.getUserBufferNames();



//    // Calculate the stride based on buffer strides, assuming tightly packed.
//    // Note: Strides = Number of bytes to advance to the next element in each dimension.
//    // For example, if a float tensor of dimension 2x4x3 is tightly packed in a buffer of 96 bytes, then the strides would be (48,12,4)
//    // Note: Buffer stride is usually known and does not need to be calculated.
//    std::vector<size_t> strides(bufferShape.rank());
//    strides[strides.size() - 1] = sizeof(float);
//    size_t stride = strides[strides.size() - 1];
//    for (size_t i = bufferShape.rank() - 1; i > 0; i--)
//    {
//      stride *= bufferShape[i];
//      strides[i-1] = stride;
//    }
//    const size_t bufferElementSize = (*bufferAttributesOpt)->getElementSize();
//    size_t bufSize = calcSizeFromDims(bufferShape.getDimensions(), bufferShape.rank(), bufferElementSize);
//    // set the buffer encoding type
//    zdl::DlSystem::UserBufferEncodingFloat userBufferEncodingFloat;
//    // create user-backed storage to load input data onto it
//    applicationBuffers.emplace(name, std::vector<uint8_t>(bufSize));
//    // create SNPE user buffer from the user-backed buffer
//    zdl::DlSystem::IUserBufferFactory& ubFactory = zdl::SNPE::SNPEFactory::getUserBufferFactory();
//    snpeUserBackedBuffers.push_back(ubFactory.createUserBuffer(applicationBuffers.at(name).data(),
//                                                              bufSize,
//                                                              strides,
//                                                              &userBufferEncodingFloat));
//    // add the user-backed buffer to the inputMap, which is later on fed to the network for execution
//    userBufferMap.add(name, snpeUserBackedBuffers.back().get());
}

//void executeNetwork(zdl::DlSystem::UserBufferMap& inputMap,
//                    zdl::DlSystem::UserBufferMap& outputMap,
//                    std::unordered_map<std::string,std::vector<uint8_t>>& applicationOutputBuffers,
//                    const std::string& outputDir,
//                    int num)
//{
//    // Execute the network and store the outputs in user buffers specified in outputMap
//    snpe->execute(inputMap, outputMap);
//    // Get all output buffer names from the network
//    const zdl::DlSystem::StringList& outputBufferNames = outputMap.getUserBufferNames();
//    // Iterate through output buffers and print each output to a raw file
//    std::for_each(outputBufferNames.begin(), outputBufferNames.end(), [&](const char* name)
//    {
//       std::ostringstream path;
//       path << outputDir << "/Result_" << num << "/" << name << ".raw";
//       SaveUserBuffer(path.str(), applicationOutputBuffers.at(name));
//    });
//}
// The following is a partial snippet of the function
void SaveUserBuffer(const std::string& path, const std::vector<uint8_t>& buffer) {

    std::ofstream os(path, std::ofstream::binary);
    if (!os)
    {
      std::cerr << "Failed to open output file for writing: " << path << "\n";
      std::exit(EXIT_FAILURE);
    }
    if (!os.write((char*)(buffer.data()), buffer.size()))
    {
      std::cerr << "Failed to write data to: " << path << "\n";
      std::exit(EXIT_FAILURE);
    }
}

void initModel() {
    zdl::DlSystem::Runtime_t runt=checkRuntime();
    initializeSNPE(runt);
}

//void initVisionStream(){
//    int err;
//    while (true) {
//        err = visionstream_init(&stream, VISION_STREAM_RGB_BACK, true, &buf_info);
//        if (err != 0) {
//            printf("visionstream fail\n");
//            usleep(100000);
//        }
//        break;
//    }
//}

//int getStreamBuffer(){
//    buf = visionstream_get(&stream, &extra);
//    if (buf == NULL) {
//        printf("visionstream get failed\n");
//        return 1;
//    }
//    return 0;
//}

//std::vector<float> processStreamBuffer(VIPCBuf* buf) {
//    uint8_t *src_ptr = (uint8_t *)buf->addr;
//    src_ptr += (top_crop * image_stride); // starting offset of 150 lines of stride in
//
//    std::vector<float> outputVector;
//    for (int line = 0; line < cropped_shape[0]; line++) {
//        for(int line_pos = 0; line_pos < (cropped_shape[1] * cropped_shape[2]); line_pos += cropped_shape[2]) {
//            outputVector.push_back(src_ptr[line_pos + offset + 0] / pixel_norm);
//            outputVector.push_back(src_ptr[line_pos + offset + 1] / pixel_norm);
//            outputVector.push_back(src_ptr[line_pos + offset + 2] / pixel_norm);
//        }
//        src_ptr += image_stride;
//    }
//    return outputVector;
//}

void sendPrediction(std::vector<float> modelOutputVec, PubSocket* traffic_lights_sock) {
    float modelOutput[4];
    for (int i = 0; i < 4; i++){  // convert vector to array
        modelOutput[i] = modelOutputVec[i];
        // std::cout << modelOutput[i] << std::endl;
    }
    // std::cout << std::endl;

    kj::ArrayPtr<const float> modelOutput_vs(&modelOutput[0], 4);

    capnp::MallocMessageBuilder msg;
    cereal::Event::Builder event = msg.initRoot<cereal::Event>();
    event.setLogMonoTime(nanos_since_boot());
    auto traffic_lights = event.initTrafficModelRaw();
    traffic_lights.setPrediction(modelOutput_vs);

    auto words = capnp::messageToFlatArray(msg);
    auto bytes = words.asBytes();
    traffic_lights_sock->send((char*)bytes.begin(), bytes.size());
}

//std::vector<float> runModel(std::vector<float> inputVector) {
//    std::unique_ptr<zdl::DlSystem::ITensor> inputTensor = loadInputTensor(snpe, inputVector);  // inputVec)
//    zdl::DlSystem::ITensor* tensor = executeNetwork(snpe, inputTensor);
//
//    std::vector<float> outputVector;
//    for (auto it = tensor->cbegin(); it != tensor->cend(); ++it ){
//        float op = *it;
//        outputVector.push_back(op);
//        std::cout << op << std::endl;
//    }
//    std::cout << "---\n";
//    return outputVector;
//}

void writeImageVector(std::vector<float> imageVector){
    ofstream outputfile("/data/cropped");
    std::cout << "written!\n";
    std::copy(imageVector.begin(), imageVector.end(), std::ostream_iterator<float>(outputfile, "\n"));
}

bool shouldStop() {
    std::ifstream infile("/data/openpilot/selfdrive/trafficd/stop");
    return infile.good();
}

void sleepFor(double sec) {
    usleep(sec * secToUs);
}

double rateKeeper(double loopTime, double lastLoop) {
    double toSleep;
    if (lastLoop < 0){  // don't sleep if last loop lagged
        lastLoop = std::max(lastLoop, -modelRate);  // this should ensure we don't keep adding negative time to lastLoop if a frame lags pretty badly
                                                    // negative time being time to subtract from sleep time
        // std::cout << "Last frame lagged by " << -lastLoop << " seconds. Sleeping for " << modelRate - (loopTime * msToSec) + lastLoop << " seconds" << std::endl;
        toSleep = modelRate - (loopTime * msToSec) + lastLoop;  // keep time as close as possible to our rate, this reduces the time slept this iter
    } else {
        toSleep = modelRate - (loopTime * msToSec);
    }
    if (toSleep > 0){  // don't sleep for negative time, in case loop takes too long one iteration
        sleepFor(toSleep);
    } else {
        std::cout << "trafficd lagging by " << -(toSleep / msToSec) << " ms." << std::endl;
    }
    return toSleep;
}

void set_do_exit(int sig) {
    std::cout << "received signal: " << sig << std::endl;
    do_exit = 1;
}

uint8_t clamp(int16_t value) {
    return value<0 ? 0 : (value>255 ? 255 : value);
}

//static std::vector<float> getFlatVector(const VIPCBuf* buf, const bool returnBGR) {
//    // returns RGB if returnBGR is false
//    const size_t width = original_shape[1];
//    const size_t height = original_shape[0];
//
//    uint8_t *y = (uint8_t*)buf->addr;
//    uint8_t *u = y + (width * height);
//    uint8_t *v = u + (width / 2) * (height / 2);
//
//    int b, g, r;
//    std::vector<float> bgrVec;
//    for (int y_cord = (original_shape[0] - hood_crop - 1); y_cord >= top_crop; y_cord--) {
//        for (int x_cord = (original_shape[1] - horizontal_crop - 1); x_cord >= horizontal_crop; x_cord--) {
//            int yy = y[(y_cord * width) + x_cord];
//            int uu = u[((y_cord / 2) * (width / 2)) + (x_cord / 2)];
//            int vv = v[((y_cord / 2) * (width / 2)) + (x_cord / 2)];
//
//            r = 1.164 * (yy - 16) + 1.596 * (vv - 128);
//            g = 1.164 * (yy - 16) - 0.813 * (vv - 128) - 0.391 * (uu - 128);
//            b = 1.164 * (yy - 16) + 2.018 * (uu - 128);
//
//            if (returnBGR){
//                bgrVec.push_back(clamp(r) / 255.0);
//                bgrVec.push_back(clamp(g) / 255.0);
//                bgrVec.push_back(clamp(b) / 255.0);
//            } else {
//                bgrVec.push_back(clamp(b) / 255.0);
//                bgrVec.push_back(clamp(g) / 255.0);
//                bgrVec.push_back(clamp(r) / 255.0);
//            }
//        }
//    }
//    // std::reverse(bgrVec.begin(), bgrVec.end());
//    return bgrVec;
//}


static std::vector<float> getFlatVector(const VIPCBuf* buf, const bool returnBGR) {
    // returns RGB if returnBGR is false
    const size_t width = original_shape[1];
    const size_t height = original_shape[0];

    uint8_t *y = (uint8_t*)buf->addr;
    uint8_t *u = y + (width * height);
    uint8_t *v = u + (width / 2) * (height / 2);

    int b, g, r;
    std::vector<float> bgrVec;
    for (int y_cord = top_crop; y_cord < (original_shape[0] - hood_crop); y_cord++) {
        for (int x_cord = horizontal_crop; x_cord < (original_shape[1] - horizontal_crop); x_cord++) {
            int yy = y[(y_cord * width) + x_cord];
            int uu = u[((y_cord / 2) * (width / 2)) + (x_cord / 2)];
            int vv = v[((y_cord / 2) * (width / 2)) + (x_cord / 2)];

            r = 1.164 * (yy - 16) + 1.596 * (vv - 128);
            g = 1.164 * (yy - 16) - 0.813 * (vv - 128) - 0.391 * (uu - 128);
            b = 1.164 * (yy - 16) + 2.018 * (uu - 128);

            if (returnBGR){
                bgrVec.push_back(clamp(b) / 255.0);
                bgrVec.push_back(clamp(g) / 255.0);
                bgrVec.push_back(clamp(r) / 255.0);
            } else {
                bgrVec.push_back(clamp(r) / 255.0);
                bgrVec.push_back(clamp(g) / 255.0);
                bgrVec.push_back(clamp(b) / 255.0);
            }
        }
    }
    return bgrVec;
}


int main(){
    signal(SIGINT, (sighandler_t)set_do_exit);
    signal(SIGTERM, (sighandler_t)set_do_exit);

    initModel(); // init stuff

    // snpe input stuff

    // snpe output stuff
    createUserBuffer();
    std::cout << "successful!\n";

    return 0;

    VisionStream stream;

    Context* c = Context::create();
    PubSocket* traffic_lights_sock = PubSocket::create(c, "trafficModelRaw");
    assert(traffic_lights_sock != NULL);
    while (!do_exit){  // keep traffic running in case we can't get a frame (mimicking modeld)
        VisionStreamBufs buf_info;
        int err = visionstream_init(&stream, VISION_STREAM_YUV, true, &buf_info);
        if (err != 0) {
            printf("trafficd: visionstream fail\n");
            usleep(100000);
        }

        double loopStart;
        double loopEnd;
        double lastLoop = 0;
        while (!do_exit){
            loopStart = millis_since_boot();

            VIPCBuf* buf;
            VIPCBufExtra extra;

            buf = visionstream_get(&stream, &extra);
            if (buf == NULL) {
                printf("trafficd: visionstream get failed\n");
                break;
            }
            std::vector<float> imageVector = getFlatVector(buf, true);  // writes float vector to inputVector
//            std::cout << "Vector size: " << imageVector.size() << std::endl; // uncomment to debug
//            writeImageVector(imageVector);
//            return 0;


            //std::vector<float> modelOutputVec = runModel(imageVector);

//            int pred_idx = std::max_element(modelOutputVec.begin(), modelOutputVec.end()) - modelOutputVec.begin();
//            std::cout << pred_idx << std::endl;
//            std::cout << "Prediction: " << modelLabels[pred_idx] << " (" << modelOutputVec[pred_idx] * 100 << "%)" << std::endl;

            //sendPrediction(modelOutputVec, traffic_lights_sock);

            //loopEnd = millis_since_boot();
            // std::cout << "Loop time: " << loopEnd - loopStart << " ms\n";
            //lastLoop = rateKeeper(loopEnd - loopStart, lastLoop);
            // std::cout << "Current frequency: " << 1 / ((millis_since_boot() - loopStart) * msToSec) << " Hz" << std::endl;
        }
    }
    std::cout << "trafficd is dead" << std::endl;
    visionstream_destroy(&stream);
    return 0;
}

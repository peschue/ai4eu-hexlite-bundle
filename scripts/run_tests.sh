
python3 -m grpc_tools.protoc --proto_path=grpcservice --python_out=tests --grpc_python_out=tests hexlite.proto &&
CONFIG=grpcservice/config.json python3 tests/test_hexlite.py
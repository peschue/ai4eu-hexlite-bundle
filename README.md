# ai4eu-hexlite-bundle

AI4EU Experiments Component containing Hexlite and several plugins:

* Stringplugin
* Testplugin
* OWLAPI Plugin

A gRPC service is implemented that permits the usage of Hexlite via a gRPC/Protobuf interface. The interface is the generic Answer Set Solver interface.

# Contents

* `grpcservice/` contains the gRPC service.
* `tests/` contains testing scripts.
* `scripts/` contains helpful scripts for testing/building/running.
* `hexlite/` contains a git submodule with the Hexlite git repo.
* `hexlite-owlapi-plugin/` contains a git submodule with the Hexlite OWLAPI plugin git repo.

# How to build this repository

* clone all submodules

    `git submodule init`
    `git submodule update`

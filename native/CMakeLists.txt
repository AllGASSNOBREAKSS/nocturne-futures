cmake_minimum_required(VERSION 3.20)
project(nocturne_native LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(nocturne_native
    bindings/bindings.cpp
    src/aggregate.cpp
)
target_include_directories(nocturne_native PRIVATE src)

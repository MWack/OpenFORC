# OpenFORC

OpenFORC implements algorithms to analyze datasets of First Order Reversal Curves (FORCs). Those are an important tool to characterize magnetic properties of materials. They are popular in Earth sciences to better understand terrestrial rocks.

The measurement protocol is based on the measurement of magnetic moments of a specimen while applying varying external magnetic fields in a specific order.

OpenFORC aims to put together different implementation ideas and investigate different measurement schemes to obtain the best information possible.

Right now a basic working pure Python implementation is available. C++ code is still in the debugging phase but will allow a more efficient implementation with bindings to popular scripting languages like Python and Matlab.

This project benefits greatly form the cooperation with Mag-Instruments (www.mag-instruments.com) who provide custom measurement routines on their VFTB machines which allows to optimize the measurement protocol itself and the analysis of the obtained data mutually.

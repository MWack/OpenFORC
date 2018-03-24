#ifndef FORC_H
#define FORC_H

#include <stdio.h>

#define DLLEXPORT extern "C" __declspec(dllexport)

DLLEXPORT void cfun(const double *indatav, size_t size, double *outdatav);
DLLEXPORT void convHaHb2HcHu(const double *Ha, const double *Hb, size_t size, double *Hc, double *Hu);
DLLEXPORT void fitPolySurface(const double *x, const double *y, const double *z, size_t size, double *a, char *msg);
DLLEXPORT void calculateFORCHcHuFit(const double *Hc, const double *Hu, const double *M, size_t sizeHc, size_t sizeHu, double *FORC, int sf);

#endif // FORC_H

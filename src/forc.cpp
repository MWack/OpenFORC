#include "forc.h"

#include <iostream>
#include <string>
#include <Eigen/Dense>

using namespace std;
using namespace Eigen;


/*! for testing only */
DLLEXPORT void cfun(const double *indatav, size_t size, double *outdatav)
{
    size_t i;
    for (i = 0; i < size; ++i)
        outdatav[i] = indatav[i] * 2.0;
	MatrixXd m(2, 2);
	m(0, 0) = 3;
	m(1, 0) = 2.5;
	m(0, 1) = -1;
	m(1, 1) = m(1, 0) + m(0, 1);
	std::cout << m << std::endl;
}


/*!
Extract block of data from 2D row mahor array
w: number of columns of input data
h: number of rows of input data
i and j are the starting indices
p and q is width and height of block
data: pointer to input data
block: pointer to at least p*q double array
*/
inline void block(size_t w, size_t h, size_t i, size_t j, size_t p, size_t q, const double* data, double* block)
{
	for (int r = j; r < j + q; r++)  // go through rows
	{
		memcpy(&block[r*p], &data[r*w + i], sizeof(double)*p);
	}
}

//! interpolate FORC raw data 
DLLEXPORT void interpolateFORCData(const double *data)
{


}

//! calculate FORC in Hc, Hu space based on polynomial fit
/*!
i.e. FORC = 1/8 * (d^2 M / dHc^2 - d^2 M / dHb^2) (Egli, 2013)
Hc and Hu must be rectangular arrays (row major) with sizeHc * sizeHu elements containing Hc and Hu coordinates
M is rectangular array with sizeHc * sizeHu elements that contains measured magnetizations
FORC must be of same dimension to receive calculate FORC distribution
sf is smoothing factor
*/
// TODO: make SF template parameter to optimize runtime
DLLEXPORT void calculateFORCHcHuFit(const double *Hc, const double *Hu, const double *M, size_t sizeHc, size_t sizeHu, double *FORC, int sf)
{
	size_t i, j;

	double a[6];
	char s[100];
	
	double *x, *y, *z;
	
	
	// get block size (should depend on Hc and Hu for VariForc algorithm)
	size_t p, q;
	
	// get block boundaries// loop through matrix and take blocks with dimension sf*2+1 centered at point of interest

	for (int u = 0; u < sizeHu; u++) // rows, Hu axis
	{
		for (int c = 0; c < sizeHc; c++) // cols, Hc axis
		{
			i = u - sf; // start row index of block
			j = c - sf; // start column index of block
			p = sf * 2 + 1; // height of block
			q = sf * 2 + 1; // width of block
			
			// adjust block not to be outside of matrix
			if (u - sf < 0) // top out of bounds
			{
				p -= sf - u; // reduce height of block
				i = 0; // start at first row
			}
			else if (u + sf >= sizeHu) p -= u + sf - sizeHu + 1; // bottom out of bounds
			
			if (c - sf < 0) // left out of bounds
			{
				q -= sf - c; // reduce width of block
				j = 0;  // start at first column
			}
			else if (c + sf >= sizeHc) q -= c + sf - sizeHc + 1; // right out of bounds

			x = new double[p*q];
			y = new double[p*q];
			z = new double[p*q];
			
			block(sizeHc, sizeHu, j, i, q, p, Hc, x);
			block(sizeHc, sizeHu, j, i, q, p, Hu, y);
			block(sizeHc, sizeHu, j, i, q, p, M, z);
			
			fitPolySurface(x, y, z, p*q, a, s);
			
			delete[] x;
			delete[] y;
			delete[] z;

			//FORC[u * sizeHc + c] = (a[2] - a[4]) / 8; // final value of FORC distribution
			FORC[u * sizeHc + c] = a[3]; // for testing
			//FORC[u * sizeHc + c] = (u==c)?1:0; // diagonal for testing
			//FORC[u * sizeHc + c] = p*q; // for testing
			//FORC[u * sizeHc + c] = mM(u,c); // reproduce original values for testing
			//if(c>sizeHu-3) FORC[u * sizeHc + c] = 1; // test max Hu - top of plot
			//if (c == sizeHc - 2) FORC[u * sizeHc + c] = -1; // test max Hc - right of plot
		}
	}
}


/*!
convert Ha - Hb (measurement) coordinates to Hc - Hu (FORC) coordinates
Ha and Hb must be provided as double arrays with size elements
Hc and Hu must provide same dimension and will be filled with Hc - Hu values
Hu = (Hb + Ha) / 2
Hc = (Hb - Ha) / 2
*/
DLLEXPORT void convHaHb2HcHu(const double *Ha, const double *Hb, size_t size, double *Hc, double *Hu)
{
	for (int c = 0; c < size; c++)
	{
		Hc[c] = (Hb[c] - Ha[c]) / 2; // B-Br = Bc (Zhao)
		Hu[c] = (Hb[c] + Ha[c]) / 2; // B+Br = Bi (Zhao)
	}
	
	/*ArrayXd vHa = Map<const ArrayXd>(Ha, size, 1);
	ArrayXd vHb = Map<const ArrayXd>(Hb, size, 1);
	
	ArrayXd vHc = (vHb - vHa) / 2;
	ArrayXd vHu = (vHb + vHa) / 2;*/
}

	

//! fit a second order 2D polynomial function to given datapoints with coordinates x, y and z
/*!
fit polynomial of the form z = a0 + a1*x + a2*x^2 + a3*y + a4*y**2 + a5*x*y
to sequence of x,y,z points
x, y, and z must be arrays of length size which contain the scattered data
a must have at least a size of 6 and will be filled with fitted parameters a0..a5
*/
DLLEXPORT void fitPolySurface(const double *x, const double *y, const double *z, size_t size, double *a, char *msg)
{
	// TODO: check handling of nan values: one nan -> result is nan --> need to remove nan points
	// TODO: add weights
	// map C arrays into eigen arrays

	// allocate arrays to hold values witout nans
	double* xn = new double[size];
	double* yn = new double[size];
	double* zn = new double[size];
	
	
	// remove any nan element
	int d = 0;
	for (int c = 0; c < size; c++)
	{
		if (!isnan(z[c]))
		{
			xn[d] = x[c];
			yn[d] = y[c];
			zn[d] = z[c];
			d++;
		}
	}
	
	if (d >= 6) // we need at least 6 points to fit a surface to it
	{
		ArrayXd vx = Map<const ArrayXd>(xn, d, 1);
		ArrayXd vy = Map<const ArrayXd>(yn, d, 1);
		VectorXd vz = Map<const ArrayXd>(zn, d, 1);
	
		// compose matrix A
		MatrixXd A(d, 6); // initialize matrix
		A.col(0) = ArrayXd::Constant(d, 1); // set first column to 1
		A.col(1) = vx;
		A.col(2) = vx * vx;
		A.col(3) = vy;
		A.col(4) = vy*vy;
		A.col(5) = vx*vy;
	
		MatrixXd aa = MatrixXd::Constant(6, 1, NAN);
		// solve least squares
		// check https://eigen.tuxfamily.org/dox/group__LeastSquares.html
		// solve least squares by normal equations
		//MatrixXd aa = (A.transpose() * A).ldlt().solve(A.transpose() * vz);
		//MatrixXd aa = A.colPivHouseholderQr().solve(vz);
	
	
		//aa = A.jacobiSvd(ComputeThinU | ComputeThinV).solve(vz);
		aa = (A.transpose() * A).ldlt().solve(A.transpose() * vz);
		//aa = A.colPivHouseholderQr().solve(vz);
		memcpy(a, aa.data(), sizeof(double) * 6);

		// msg for easy debugging from python side
		/*stringstream s;
		s << "Matrix aa is:" <<
			aa << " d:" << d << endl;
		string str = s.str();
		strcpy(msg, str.c_str());*/
	}
	else
	{
		for (int c = 0; c < 6; c++) a[c] = NAN; // set all coefficients to NAN since we didn't fit anything
	}

	a[0] = d;
	
	if( d >= 6)
	{
		a[1] = xn[0];
		a[2] = yn[0];
		a[3] = zn[0];
	}
	// free memory
	delete[] xn;
	delete[] yn;
	delete[] zn;
}

DLLEXPORT void test(char *msg)
{
	MatrixXf A = MatrixXf::Random(3, 2);
	VectorXf b = VectorXf::Random(3);
	stringstream s;
	
	/*s << "The solution using normal equations is:\n" <<
		(A.transpose() * A).ldlt().solve(A.transpose() * b) << endl;*/
	s << "A block:\n" << A << "\n" <<
		A.block(0,0,2,2) << endl;
	string str = s.str();
	strcpy(msg, str.c_str());
}
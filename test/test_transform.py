#!/usr/bin/env python
# -*- coding: utf8 -*-
#
#    Project: Sift implementation in Python + OpenCL
#             https://github.com/kif/sift_pyocl
#

"""
Test suite for transformation kernel
"""

from __future__ import division

__authors__ = ["Jérôme Kieffer"]
__contact__ = "jerome.kieffer@esrf.eu"
__license__ = "BSD"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
__date__ = "2013-05-28"
__license__ = """
Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

"""

import time, os, logging
import numpy
import pyopencl, pyopencl.array
import scipy, scipy.misc, scipy.ndimage, pylab
import sys
import unittest
from utilstest import UtilsTest, getLogger, ctx
from test_image_functions import * #for Python implementation of tested functions
from test_image_setup import *
import sift
from sift.utils import calc_size
logger = getLogger(__file__)
if logger.getEffectiveLevel() <= logging.INFO:
    PROFILE = True
    queue = pyopencl.CommandQueue(ctx, properties=pyopencl.command_queue_properties.PROFILING_ENABLE)
    import pylab
else:
    PROFILE = False
    queue = pyopencl.CommandQueue(ctx)

SHOW_FIGURES = False
USE_CPU = False



print "working on %s" % ctx.devices[0].name





class test_transform(unittest.TestCase):
    def setUp(self):
        
        kernel_path = os.path.join(os.path.dirname(os.path.abspath(sift.__file__)), "transform.cl")
        kernel_src = open(kernel_path).read()
        self.program = pyopencl.Program(ctx, kernel_src).build() #.build('-D WORKGROUP_SIZE=%s' % wg_size)
        self.wg = (1, 128)



    def tearDown(self):
        self.program = None
        
        

    def test_transform(self):
        '''
        tests transform kernel
        '''    
#        image = scipy.misc.imread(os.path.join("../../test_images/","esrf_grenoble.jpg"),flatten=True).astype(numpy.float32)
        image = scipy.misc.lena().astype(numpy.float32)
        image = numpy.ascontiguousarray(image[0:410,0:352])
        
        image_height, image_width = image.shape
        output_height, output_width = int(image_height*numpy.sqrt(2)), int(image_width*numpy.sqrt(2))

        #transformation
        angle = 0.35 #numpy.pi/5.0
#        matrix = numpy.array([[numpy.cos(angle),-numpy.sin(angle)],[numpy.sin(angle),numpy.cos(angle)]],dtype=numpy.float32)
        matrix = numpy.array([[2.0,-1.5],[0.7,2.0]],dtype=numpy.float32)
        #important for float4
        matrix_for_gpu = matrix.reshape(4,1)
        offset_value = numpy.array([-0.0, -0.0],dtype=numpy.float32)
        fill_value = numpy.float32(0.0)
        mode = numpy.int32(0)
        
        wg = 1,1
        shape = calc_size((output_width,output_height), self.wg)
        
        gpu_image = pyopencl.array.to_device(queue, image)
        gpu_output = pyopencl.array.empty(queue, (output_height, output_width), dtype=numpy.float32, order="C")
        gpu_matrix = pyopencl.array.to_device(queue,matrix_for_gpu)
        gpu_offset = pyopencl.array.to_device(queue,offset_value)
        image_height, image_width = numpy.int32((image_height, image_width))
        output_height, output_width = numpy.int32((output_height, output_width))
        
        t0 = time.time()
        k1 = self.program.transform(queue, shape, wg,
        		gpu_image.data, gpu_output.data, gpu_matrix.data, gpu_offset.data, 
        		image_width, image_height, output_width, output_height, fill_value, mode)
        res = gpu_output.get()
        t1 = time.time()

        ref = scipy.ndimage.interpolation.affine_transform(image,matrix,
        	offset=offset_value, output_shape=(output_height,output_width), 
        	order=1, mode="constant", cval=fill_value)
        t2 = time.time()
        
        delta = abs(res-ref)
        delta_arg = delta.argmax()
        delta_max = delta.max()
        at_0, at_1 = delta_arg/output_width, delta_arg%output_width
        print("Max error: %f at (%d, %d)" %(delta_max, at_0, at_1))
        print res[at_0,at_1]
        print ref[at_0,at_1]
        
        SHOW_FIGURES = True
        if SHOW_FIGURES:
            fig = pylab.figure()
            sp1 = fig.add_subplot(221,title="Output")
            sp1.imshow(res, interpolation="nearest")
            sp2 = fig.add_subplot(222,title="Reference")
            sp2.imshow(ref, interpolation="nearest")
            sp3 = fig.add_subplot(223,title="delta (max = %f)" %delta_max)
            sh3 = sp3.imshow(delta[:,:], interpolation="nearest")
            cbar = fig.colorbar(sh3)
            fig.show()
            raw_input("enter")


        if PROFILE:
            logger.info("Global execution time: CPU %.3fms, GPU: %.3fms." % (1000.0 * (t2 - t1), 1000.0 * (t1 - t0)))
            logger.info("Transformation took %.3fms" % (1e-6 * (k1.profile.end - k1.profile.start)))
            
            
            
            

def test_suite_transform():
    testSuite = unittest.TestSuite()
    testSuite.addTest(test_transform("test_transform"))
    return testSuite

if __name__ == '__main__':
    mysuite = test_suite_transform()
    runner = unittest.TextTestRunner()
    if not runner.run(mysuite).wasSuccessful():
        sys.exit(1)


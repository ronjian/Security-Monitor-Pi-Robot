#!/usr/bin/python3

# borrow from ncappzoo project

# ****************************************************************************
# Copyright(c) 2017 Intel Corporation. 
# License: MIT See LICENSE file in root directory.
# ****************************************************************************

# DIY smart security camera PoC using Raspberry Pi Camera and 
# Intel® Movidius™ Neural Compute Stick (NCS)

import os
import sys
import numpy
import select
import ntpath
import argparse
import mvnc.mvncapi as mvnc
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
from time import localtime, strftime


# "Class of interest" - Display detections only if they match this class ID
CLASS_PERSON         = 15

# Detection threshold: Minimum confidance to tag as valid detection
CONFIDANCE_THRESHOLD = 0.8

# Variable to store commandline arguments
parser = argparse.ArgumentParser(
                     description="DIY smart security camera using \
                     Rapberry Pi Camera and Intel® Movidius™ Neural Compute Stick. \
                     \n Hit <ENTER> to terminate program." )

parser.add_argument( '-g', '--graph', type=str,
                     default='nc_app/graph',
                     help="Absolute path to the neural network graph file." )

parser.add_argument( '-l', '--labels', type=str,
                     default='nc_app/labels.txt',
                     help="Absolute path to labels file." )

parser.add_argument( '-M', '--mean', type=float,
                     nargs='+',
                     default=[127.5, 127.5, 127.5],
                     help="',' delimited floating point values for image mean." )

parser.add_argument( '-S', '--scale', type=float,
                     default=0.00789,
                     help="Absolute path to labels file." )

parser.add_argument( '-D', '--dim', type=int,
                     nargs='+',
                     default=[300, 300],
                     help="Image dimensions. ex. -D 224 224" )

parser.add_argument( '-c', '--colormode', type=str,
                     default="bgr",
                     help="RGB vs BGR color sequence. This is network dependent." )

ARGS = parser.parse_args()

# Load the labels file 
labels =[ line.rstrip('\n') for line in 
          open( ARGS.labels ) if line != 'classes\n'] 

# ---- Step 1: Open the enumerated device and get a handle to it -------------

def open_ncs_device():

    # Look for enumerated NCS device(s); quit program if none found.
    # devices = mvnc.EnumerateDevices()
    devices = mvnc.enumerate_devices()
    if len( devices ) == 0:
        print( "No devices found" )
        quit()

    # Get a handle to the first enumerated device and open it
    device = mvnc.Device( devices[0] )
    # device.OpenDevice()
    device.open()

    return device

# ---- Step 2: Load a graph file onto the NCS device -------------------------

def load_graph( device ):

    # Read the graph file into a buffer
    with open( ARGS.graph, mode='rb' ) as f:
        graph_buffer = f.read()



    # Load the graph buffer into the NCS
    # graph = device.AllocateGraph( graph_buffer )
    graph = mvnc.Graph('secure_cam_graph')
    graph.allocate(device, graph_buffer)

    # Get the graphTensorDescriptor structs (they describe expected graph input/output)
    # input_descriptors = graph.get_option(mvnc.GraphOption.RO_INPUT_TENSOR_DESCRIPTORS)
    # output_descriptors = graph.get_option(mvnc.GraphOption.RO_OUTPUT_TENSOR_DESCRIPTORS)

    # Create input/output Fifos
    # input_fifo = mvnc.Fifo('input1', mvnc.FifoType.HOST_WO)
    # output_fifo = mvnc.Fifo('output1', mvnc.FifoType.HOST_RO)
    # input_fifo.allocate(device, input_descriptors[0], 2)
    # output_fifo.allocate(device, output_descriptors[0], 2)
    input_fifo, output_fifo = graph.allocate_with_fifos(device, graph_buffer)



    return graph, input_fifo, output_fifo

# ---- Step 3: Pre-process the images ----------------------------------------

def pre_process_image( frame ):

    # Read & resize image
    # [Image size is defined by choosen network, during training]
    img = Image.fromarray( frame )
    img = img.resize( ARGS.dim )
    img = numpy.array( img )

    # Mean subtraction & scaling [A common technique used to center the data]
    img = img.astype( numpy.float32 )
    img = ( img - numpy.float32( ARGS.mean ) ) * ARGS.scale

    return img

# ---- Step 4: Read & print inference results from the NCS -------------------

def infer_image( graph, input_fifo, output_fifo , img, frame ):

    detect_flg = False

    # # Load the image as a half-precision floating point array
    # graph.LoadTensor( img, 'user object' )

    # # Get the results from NCS
    # output, userobj = graph.GetResult()
    
    # Write the image to the input queue and queue the inference in one call
    graph.queue_inference_with_fifo_elem(input_fifo, output_fifo, img, None)

    # Get the results from the output queue
    output, userobj = output_fifo.read_elem()


    # Get execution time
    # inference_time = graph.GetGraphOption( mvnc.GraphOption.TIME_TAKEN )

    # Deserialize the output into a python dictionary
    output_dict = _ssd( 
                      output, 
                      CONFIDANCE_THRESHOLD, 
                      frame.shape )
    # Print the results (each image/frame may have multiple objects)
    for i in range( 0, output_dict['num_detections'] ):

        # Filter a specific class/category
        if( output_dict.get( 'detection_classes_' + str(i) ) == CLASS_PERSON ):
            detect_flg = True

        # cur_time = strftime( "%Y_%m_%d_%H_%M_%S", localtime() )
        # print( "Person detected on " + cur_time )

        # Extract top-left & bottom-right coordinates of detected objects 
        (y1, x1) = output_dict.get('detection_boxes_' + str(i))[0]
        (y2, x2) = output_dict.get('detection_boxes_' + str(i))[1]

        # Prep string to overlay on the image
        display_str = ( 
            labels[output_dict.get('detection_classes_' + str(i))]
            + ": "
            + str( output_dict.get('detection_scores_' + str(i) ) )
            + "%" )

        # Overlay bounding boxes, detection class and scores
        frame = _draw_bounding_box( 
                    y1, x1, y2, x2, 
                    frame,
                    thickness=4,
                    color=(255, 255, 0),
                    display_str=display_str )

        # Capture snapshots
        # img = Image.fromarray( frame )
        # photo = ( os.path.dirname(os.path.realpath(__file__))
        #           + "/captures/photo_"
        #           + cur_time + ".jpg" )
        # img.save( photo )

    # If a display is available, show the image on which inference was performed
    # if 'DISPLAY' in os.environ:
    #     img.show()
    return frame, detect_flg

# ---- Step 5: Unload the graph and close the device -------------------------

def close_ncs_device( device, graph, input_fifo, output_fifo ):
    # graph.DeallocateGraph()
    # device.CloseDevice()
    input_fifo.destroy()
    output_fifo.destroy()
    graph.destroy()
    device.close()
    device.destroy()

def _ssd( output, confidance_threshold, shape ):

    # Dictionary where the deserialized output will be stored
    output_dict = {}

    # Extract the original image's shape
    height, width, channel = shape

    # Total number of detections
    output_dict['num_detections'] = int( output[0] )

    # Variable to track number of valid detections
    valid_detections = 0

    for detection in range( output_dict['num_detections'] ):

        # Skip the first 7 values, and point to the next batch of 7 values
        base_index = 7 + ( 7 * detection )

        # Record only those detections whose confidance meets our threshold
        if( output[ base_index + 2 ] > confidance_threshold ):

            output_dict['detection_classes_' + str(valid_detections)] = \
                int( output[base_index + 1] )

            output_dict['detection_scores_' + str(valid_detections)] = \
                int( output[base_index + 2] * 100 )

            x = [ int( output[base_index + 3] * width ), 
                  int( output[base_index + 5] * width ) ]

            y = [ int( output[base_index + 4] * height ), 
                  int( output[base_index + 6] * height ) ]

            output_dict['detection_boxes_' + str(valid_detections)] = \
                list( zip( y, x ) )

            valid_detections += 1

    # Update total number of detections to valid detections
    output_dict['num_detections'] = int( valid_detections )

    return( output_dict )

def _draw_bounding_box( y1, x1, y2, x2, 
                       img, 
                       thickness=4, 
                       color=(255, 255, 0),
                       display_str=() ):

    """ Inputs
    (x1, y1)  = Top left corner of the bounding box
    (x2, y2)  = Bottom right corner of the bounding box
    img       = Image/frame represented as numpy array
    thickness = Thickness of the bounding box's outline
    color     = Color of the bounding box's outline
    """

    img = Image.fromarray( img )
    draw = ImageDraw.Draw( img )

    for x in range( 0, thickness ):
        draw.rectangle( [(x1-x, y1-x), (x2-x, y2-x)], outline=color )

    font = ImageFont.load_default()
    draw.text( (x1, y1), display_str, font=font )

    return numpy.array( img )
# ==== End of file ===========================================================

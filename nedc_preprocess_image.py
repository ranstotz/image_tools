#!/usr/bin/env python
#
# file: ${NEDC_NFC}/util/python/nedc_preprocess_image.py
#
# revision history:
#  20180603 (CC): initial version
#  20180603 (RA): format and classes added
#  20180610 (RA): add jpeg and png methods
#  20180613 (CC): add numpy array method
#  20180614 (RA): add std ISIP tools to replace existing code
#  20180615 (RA): separate class and driver to ISIP standard
#  20180619 (RA): finalize working script with class interface
#  20180620 (RA): continue adding isip features and functionality
#  20180621 (RA): debugging and testing
#  20180703 (CC): address comments
# 
# This utility makes use of the nedc_image_tools Preprocess class
# to handle some of the basic image preprocessing operations, mostly
# relating to converting between file extensions and some of the most common
# image transformations (e.g Gaussian/Laplacian, grayscale, rescale)
#------------------------------------------------------------------------------

# import system modules
#
import sys
import os

# import 3rd-party modules
#
import numpy as np
import openslide
import cv2

# import NEDC modules
#
import nedc_cmdl_parser as ncp
import nedc_file_tools as nft
import nedc_image_tools as nit

#------------------------------------------------------------------------------
#
# global variables are listed here
#
#------------------------------------------------------------------------------

# get the location of $NEDC_NFC out of the environment
#
NEDC_NFC = os.environ['NEDC_NFC']

# define the locations of the help and usage
#
HELP_FILE = \
      NEDC_NFC + \
      "/util/python/nedc_preprocess_image/nedc_preprocess_image.help"
USAGE_FILE = \
      NEDC_NFC + \
      "/util/python/nedc_preprocess_image/nedc_preprocess_image.usage"

# define default argument values
#
PARAM_FILE = \
      NEDC_NFC + "/util/python/nedc_preprocess_image/params/params.txt"
ODIR = NEDC_NFC + "/util/python/nedc_preprocess_image/output"
RDIR = None
IFILE = \
      NEDC_NFC + "/util/python/nedc_preprocess_image/lists/images.list"

# create list for image conversion formats
#
valid_image_formats = ['bmp', 'dib', 'jpeg', 'jpg', 'jpe', 'jp2', \
                       'png', 'pbm', 'pgm', 'ppm', 'sr', 'ras', \
                       'tiff', 'tif']
#define version string
#
__version__ = "0.1.0-alpha"


# define error constants
#
NEDC_DEF_MAKEDIRS_ERROR = 17

#------------------------------------------------------------------------------
#
# the main program starts here
#
#------------------------------------------------------------------------------
#
# method: main
#
# arguments: none
#
# return: none
#
# This function is the main program.
#
#
def main(argv):

  # define local variables
  #
  odir = ODIR
  params = PARAM_FILE
  rdir = RDIR
  ifile = IFILE
  
  # defines the default file extension to print to (i.e. raw rgb pixel data)
  #
  ext = 'raw'
  
  # create command line parser
  #
  parser = ncp.CommandLineParser(USAGE_FILE, HELP_FILE)
  
  # define command line arguments
  #
  parser.add_argument("files", type = str, nargs='*')
  parser.add_argument("--version", action='version', version=__version__)
  parser.add_argument("-parameters", "-p", "-pfile", type = str)
  parser.add_argument("-odir", "-o", "-output", type = str)
  parser.add_argument("-rdir", "-r", "-replace", type = str)
  parser.add_argument("-ofmt", "-format", type = str)
  parser.add_argument("-help", action="help")

  # parse the command line
  #
  args = parser.parse_args()
  
  # print usage file if no cmdl arguments provided and exit
  #
  if not args.files:
    parser.print_usage()
    exit(-1)
  
  # set options and argument values provided 
  #
  if args.parameters:
    pfile = args.parameters
    
  if args.odir:
    odir = args.odir

  if args.rdir:
    rdir = args.rdir
  
  if args.ofmt:
    image_format = args.ofmt

    # set extension to image format, strip period for formatting
    #
    ext = image_format.replace(".", "")
    
    # check if image format is valid, prompts user with valid
    # formats. Exits script if invalid.
    #
    if image_format not in valid_image_formats:
        print  "%s (%s: %s): format %s not supported" \
            % (sys.argv[0], __name__, "main", image_format)
        sys.exit(-1)

  # load parameters from param file
  #
  parameters = nft.load_parameters(pfile, "")
  if (parameters == None):
    print  "%s (%s: %s): error loading the parameter file (%s)" % \
      (sys.argv[0], __name__, "main", pfile)
    sys.exit(-1)


  parameters.update(nft.load_parameters(params, "RESCALE_IMAGE"))
  
  parameters.update(nft.load_parameters(params, "SVS_SLIDE_LEVEL"))

  parameters.update(nft.load_parameters(params, "GAUSSIAN_VARS"))

  parameters.update(nft.load_parameters(params, "OUTPUT_FORMAT"))

  # load file list
  #
  flist = nft.get_flist(args.files[0])
  
  # check if file list was was provided
  #
  if flist is None:
    
    # if not, set flist to default global variable
    #
    flist = ifile 
  
  # create class instance to be modified
  #
  ppi = nit.Preprocess(parameters)

  # create dictionary to store methods to be called
  # 

  method_dict = {"grayscale": ppi.grayscale_image,
       "rescale": ppi.rescale,
       "display": ppi.display_image,
       "gaussian": ppi.gaussian_blur,
       "laplacian": ppi.laplacian_transform
     }
 
  # image flag, checks if images were passed or file list
  #
  image_flag = False
  
  # test if command line args are files or file lists
  # image_flags is a dictionary with the same length as the # of file arguments
  # provided.  True means that the file is an image and 0 means that it isn't.
  # if ppi.is_image() returns False it will be treated as a .list
  #
  image_flags = {}

  for file in args.files:
    if ppi.is_image(file) == True:
      image_flags[file] = True
    else:
      image_flags[file] = False

  flist = args.files
        
  # generate list of methods to complete for each image from
  # the param file, comma delimited from param file.
  #
  method_list = parameters['methods'].split(',')
  
  # display to user methods invoked
  #
  print "methods invoked: ", method_list

  # create function for implementing preprocessing functions (this is here
  # so that it has access to the local variables in the main function)
  #
  def _preprocess_image(file):
    # Recreate instance of class
    #
    ppi = nit.Preprocess(parameters)

    # create a numpy array from image data for initialization
    # this allows methods to be applied since they operate on the array
    #
    image = ppi.create_np_array(file)

    # iterate over methods to apply to image from param file
    # map to dictionary
    #
    for method in method_list:
      image = method_dict[method](image)

    # display image in new window according to param file
    #
    if parameters['display_image'] == 'True':
      method_dict['display'](image)

    # create output file path name
    #
    ofile = nft.make_ofile(file, ext, odir, rdir)

    # create output directory
    #
    try:
        os.makedirs(os.path.dirname(ofile))
    except OSError as e:
        if e.errno != NEDC_DEF_MAKEDIRS_ERROR:
            raise


    # write file to output directory (odir) safely
    #
    with open(ofile, "w") as ofile_fp:

      # check if output format parameter provided and not an svs file
      #
      if parameters['output_format'] and not file.endswith('svs'):
        ofile_fp.write(ppi.convert_image(parameters['output_format'], image))

      # write numpy array to binary file output
      #
      else:
        image.tofile(ofile)

   
  # iterate through the files in the file list or command line
  #

  for f in flist:
    # clause for handling image files passed through the command line
    #
    if image_flags[f]:
      _preprocess_image(f)
    else:
      img_list = nft.get_flist(nft.get_fullpath(f))
      for img in img_list:
        _preprocess_image(img)
 
  # exit gracefully
  #
  return     
    
# begin gracefully
#
if __name__ == "__main__":
  main(sys.argv[1:])

# 
# end of file

  

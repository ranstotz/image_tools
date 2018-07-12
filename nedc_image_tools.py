#!/usr/bin/env python
#
# file: ${NEDC_NFC}/class/python/nedc_preprocess_tools/nedc_preprocess_tools.py
#
# revision history:
#  20180617 (RA): separate class and driver to ISIP standard
#  20180620 (RA): comment code
#
# usage:
#  import nedc_preprocess_tools as npt
#
# This class contains methods to process images
#
#------------------------------------------------------------------------------

# import system modules
#
import sys
import os
import openslide
import cv2
import numpy as np

# import NEDC modules
#
import nedc_cmdl_parser as ncp
import nedc_file_tools as nft

#------------------------------------------------------------------------------
#
# global variables are listed here
#
#------------------------------------------------------------------------------

__version__ = "0.1.0-alpha"

#------------------------------------------------------------------------------
#
# classes are listed here
#
#------------------------------------------------------------------------------

# class: Preprocess
#
# This is the main class of nedc_preprocess_tools, it contains methods to 
# modify an image
#
class Preprocess:

  # method: constructor
  # 
  # arguments: parameter file dictionary
  #
  # returns: none
  #
  def __init__(self, params_a):
    self.params_d = params_a
  # 
  # end of method
  
  # method: is_image
  #
  # arguments: 
  #  file: an image file or other
  #
  # returns: True if file is an acceptable image file
  #
  # This method tests for Aperio formats (svs and tif) or OpenCV
  # formats returning false if neither.
  #
  def is_image(self, ifile_a):
    
    # local variables
    # list acceptable Aperio image extensions
    #
    aperio_ext1 = '.svs'
    aperio_ext2 = '.tif'
    
    # check if image is Aperio slide format (.svs or .tif)
    # then open image using OpenSlide
    #
    if ifile_a.endswith(aperio_ext1) or ifile_a.endswith(aperio_ext2):
      

      # try to open image with applicable extensions
      #
      try:
        image = openslide.OpenSlide(ifile_a)
        
        # test if image successfully loaded without error
        #
        if image is not None:
          
          # retrun true if image successfully loaded 
          #
          return True

        # otherwise return false
        #
        else: 
          return False

      # return false if opening image returns an error
      #
      except:
        return False

    # try opening file with opencv if not Aperio format
    #
    try:
      image = cv2.imread(ifile_a, cv2.IMREAD_COLOR)
     
      # test if image successfully loaded without error
      #
      if image is not None:
       
        # return true if image successfully loaded
        #
        return True

      # otherwise return false
      #
      else:
        return False

    # return false if opening image returns an error
    #
    except:
      return False
  # 
  # end of method

  # method: create_np_array
  #
  # arguments: 
  #  file: image file
  # 
  # returns: numpy array of RGB values
  #
  # This method is used to create a numpy array from an 
  # input image file (.svs) whole slide image or opencv format
  #
  def create_np_array(self, ifile_a):
    
    # local variables
    # list acceptable Aperio image extensions
    #
    aperio_ext1 = '.svs'
    aperio_ext2 = '.tif'
    print ifile_a
    # check if image is Aperio slide format (.svs or .tif)
    # then open image using OpenSlide
    #
    if ifile_a.endswith(aperio_ext1) or ifile_a.endswith(aperio_ext2):
      
      # open file using OpenSlide library
      #
      slide = openslide.OpenSlide(ifile_a)
      
      # save image magnification level to variable
      #
      slide_lvl = int(self.params_d['svs_slide_level'])
      
      # store proper magnification
      #
      slide_dim = slide.level_dimensions[slide_lvl]
      
      # store image to np array
      #
      np_img = np.asarray(slide.read_region((0,0), slide_lvl, slide_dim))
      
      # return np array
      #
      return np_img

    # otherwise return np array from opencv
    #
    return cv2.imread(ifile_a, cv2.IMREAD_COLOR)
  # 
  # end of method

  # method: rescale
  #
  # arguments: 
  #  file: numpy array of RGB values
  # 
  # returns: a rescaled, padded numpy array with specified background
  # color
  #
  def rescale(self, img_a):
    
    # save param file variable 
    #
    max_scaled_dim = int(self.params_d['max_scaled_dim'])
    
    # read the background color as a hex (base-16) number from the parameter 
    # file.
    #
    bckg_color = int(self.params_d['background_color'], 16)
   
    # get the 8-bit channel values from the original hex value with
    # bit-masking.  The pattern for the bit-masking is as follows:
    # blue mask:  00000000000000000000000011111111
    # breen mask: 00000000000000001111111100000000
    # red mask:   00000000111111110000000000000000
    # alpha-mask: 11111111000000000000000000000000
    #
    b     =  bckg_color   &  255
    g     =  (bckg_color  & (255 <<  8)) >> 8
    r     =  (bckg_color  & (255 << 16)) >> 16
    alpha =  (bckg_color  & (255 << 24)) >> 24

    # initialize padded_img as a max_dim x max_dim blank white image.  We need
    # an alpha channel here because the slides have an alpha-channel.
    # Another option might be to just take that off the slide images since we
    # don't really need that.
    #
    padded_img = np.asarray([[[r,g,b,alpha]] * max_scaled_dim] * \
          max_scaled_dim, dtype=np.uint8)

    # get the image dimensions (we need to flip the entries since when an image
    # is stored in a np array, the 1st entry is the height (i.e. the # of rows)
    # so img_dims is a np array with elements (width, height)
    #
    img_dims = np.flip(img_a.shape[:2], axis=0)

    # get the zoom factor, which represents the scaling constant to apply to
    # each dimension.  max_dim/img_dims will give the 2 scaling constants,
    # which will scale the width and height to the desired resolution, 
    # respectively.  Taking the mininum of the 2 will scale the larger
    # dimension down to max_dim, which guarantees that both dimensions
    # will <= max_dim.
    #
    zoom = np.min(float(max_scaled_dim)/img_dims)

    # compute the dimensions of the re-sized image.
    #
    resized_dims = tuple((zoom*img_dims).astype(int))

    # use cv2.resize to resize the image
    #
    resized_img = cv2.resize(img_a, resized_dims)

    # this step superimposes the rescaled image on top of the whitespace image
    #
    padded_img[:resized_dims[1],:resized_dims[0],:] = resized_img

    # return the result
    #
    return padded_img
  #
  # end of method
    
  # method: display_image
  #
  # arguments:
  #  file: numpy array of RGB values
  #
  # returns: None
  #
  # This method displays the image in another window
  #
  def display_image(self, img_a):
    
    # display image in new window
    #
    cv2.imshow('Slide Image Display', img_a)
    cv2.waitKey(0)
    
    # return gracefully
    #
    return
  #
  # end of method
    
  # method: grayscale_image
  #
  # arguments:
  #  file: numpy array of RGB values
  #
  # returns: numpy array of grayscale RGB values
  #
  # This method grayscales image 
  #
  def grayscale_image(self, img_a):
      
    # return grayscaled image
    #
    return cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY)
  # 
  # end of method

  # method: gaussian_blur
  #
  # arguments:
  #  file: numpy array of RGB values
  #
  # returns: numpy array of modified RGB values
  #
  # method to apply a gaussian blur to the image
  #
  def gaussian_blur(self, img_a):
    
    # set gaussian blur level
    #
    gauss_lvl = int(self.params_d['gauss_lvl'])
    
    # return image with a Gaussian blur
    #
    return cv2.GaussianBlur(img_a,(gauss_lvl,gauss_lvl),gauss_lvl)
  #
  # end of method
  
  # method: laplacian_transform
  #
  # arguments: 
  #  file: numpy array of RGB values
  #
  # returns: numpy array of modified RGB values
  #
  # method to apply a laplacian transform to the image
  #
  def laplacian_transform(self, img_a):

    # return image with a Laplacian transform
    #
    return cv2.Laplacian(img_a, cv2.CV_64F)
  #
  # end of method

  # method: convert_image
  # 
  # arguments:
  #  format: image format (e.g. 'jpg', 'png')
  #  file: numpy array of RGB values
  #
  # returns: encoded image according to format
  #
  # method to convert image from numpy array to specified format
  #
  def convert_image(self, format_a, img_a):
        
    # return image in valid format
    #
    return cv2.imencode(format_a, img_a)[1]
  #
  # end of method
#
# end of class
#
# end of file

  


__all__ = ['invariant_image_similarity',
           'convolve_image']

import math
from tempfile import mktemp

import numpy as np
import pandas as pd

from .. import lib
from .. import utils
from ..core import ants_image as iio



_supported_ptypes = {'unsigned char', 'unsigned int', 'float', 'double'}
_short_ptype_map = {
    'unsigned char' : 'UC',
    'unsigned int': 'UI',
    'float': 'F',
    'double' : 'D'
}

_invariant_image_similarity_dict = {
    2 : {
        'Affine': 'invariantImageSimilarity_Affine2D',
        'Similarity': 'invariantImageSimilarity_Similarity2D',
        'Rigid': 'invariantImageSimilarity_Rigid2D'
    },
    3 : {
        'Affine': 'invariantImageSimilarity_Affine3D',
        'Similarity': 'invariantImageSimilarity_Similarity3D',
        'Rigid': 'invariantImageSimilarity_Rigid3D'
    }
}

# pick up lib.convolveImageX functions
_convolve_image_dict = {}
for ndim in {2,3,4}:
    _convolve_image_dict[ndim] = 'convolveImageF%i' % ndim


def invariant_image_similarity(in_image1, in_image2, 
                                local_search_iterations=0, metric='MI', 
                                thetas=np.linspace(0,360,5),
                                thetas2=np.linspace(0,360,5),
                                thetas3=np.linspace(0,360,5),  
                                scale_image=1, do_reflection=False,
                                txfn=None, transform='Affine'):
    """
    Similarity metrics between two images as a function of geometry

    Compute similarity metric between two images as image is rotated about its
    center w/ or w/o optimization

    ANTsR function: `invariantImageSimilarity`

    Arguments
    ---------
    in_image1 : ANTsImage
        reference image
    
    in_image2 : ANTsImage
        moving image
    
    local_search_iterations : integer
        integer controlling local search in multistart
    
    metric : string
        which metric to use
            MI
            GC
    thetas : 1D-ndarray/list/tuple
        numeric vector of search angles in degrees
    
    thetas2 : 1D-ndarray/list/tuple
        numeric vector of search angles in degrees around principal axis 2 (3D)
    
    thetas3 : 1D-ndarray/list/tuple
        numeric vector of search angles in degrees around principal axis 3 (3D)
    
    scale_image : scalar
        global scale
    
    do_reflection : boolean
        whether to reflect image about principal axis
    
    txfn : string (optional)
        if present, write optimal tx to .mat file
    
    transform : string
        type of transform to use
            Rigid
            Similarity
            Affine 

    Returns
    -------
    pd.DataFrame
        dataframe with metric values and transformation parameters

    Example
    -------
    >>> import ants
    >>> img1 = ants.image_read(ants.get_ants_data('r16'))
    >>> img2 = ants.image_read(ants.get_ants_data('r64'))
    >>> metric = ants.invariant_image_similarity(img1,img2)
    """
    if transform not in {'Rigid', 'Similarity', 'Affine'}:
        raise ValueError('transform must be one of Rigid/Similarity/Affine')

    if in_image1.pixeltype != 'float':
        in_image1 = in_image1.clone('float')
    if in_image2.pixeltype != 'float':
        in_image2 = in_image2.clone('float')

    if txfn is None:
        txfn = mktemp(suffix='.mat')

    # convert thetas to radians
    thetain = (thetas * math.pi) / 180.
    thetain2 = (thetas2 * math.pi) / 180.
    thetain3 = (thetas3 * math.pi) / 180.

    in_image1 = utils.iMath(in_image1, 'Normalize')
    in_image2 = utils.iMath(in_image2, 'Normalize')

    idim = in_image1.dimension
    fpname = ['FixedParam%i'%i for i in range(1,idim+1)]

    if not do_reflection:
        invariant_image_similarity_fn = lib.__dict__[_invariant_image_similarity_dict[idim][transform]]
        r1 = invariant_image_similarity_fn(in_image1.pointer, 
                                            in_image2.pointer,
                                            list(thetain), 
                                            list(thetain2), 
                                            list(thetain3),
                                            local_search_iterations, 
                                            metric,
                                            scale_image, 
                                            int(do_reflection),
                                            txfn)
        r1 = np.asarray(r1)

        pnames = ['Param%i'%i for i in range(1,r1.shape[1])]
        pnames[(len(pnames)-idim):len(pnames)] = fpname

        r1 = pd.DataFrame(r1, columns=['MetricValue']+pnames)
        return r1, txfn
    else:
        txfn1 = mktemp(suffix='.mat')
        txfn2 = mktemp(suffix='.mat')
        txfn3 = mktemp(suffix='.mat')
        txfn4 = mktemp(suffix='.mat')

        invariant_image_similarity_fn = lib.__dict__[_invariant_image_similarity_dict[idim][transform]]

        ## R1 ##
        r1 = invariant_image_similarity_fn(in_image1.pointer,
                                            in_image2.pointer,
                                            list(thetain), 
                                            list(thetain2), 
                                            list(thetain3),
                                            local_search_iterations, 
                                            metric,
                                            scale_image, 
                                            0,
                                            txfn1)
        r1 = np.asarray(r1)
        pnames = ['Param%i'%i for i in range(1,r1.shape[1])]
        pnames[(len(pnames)-idim):len(pnames)] = fpname
        r1 = pd.DataFrame(r1, columns=['MetricValue']+pnames)

        ## R2 ##
        r2 = invariant_image_similarity_fn(in_image1.pointer,
                                            in_image2.pointer,
                                            list(thetain), 
                                            list(thetain2), 
                                            list(thetain3),
                                            local_search_iterations, 
                                            metric,
                                            scale_image, 
                                            1,
                                            txfn2)
        r2 = np.asarray(r2)
        r2 = pd.DataFrame(r2, columns=['MetricValue']+pnames)

        ## R3 ##
        r3 = invariant_image_similarity_fn(in_image1.pointer,
                                            in_image2.pointer,
                                            list(thetain), 
                                            list(thetain2), 
                                            list(thetain3),
                                            local_search_iterations, 
                                            metric,
                                            scale_image, 
                                            2,
                                            txfn3)
        r3 = np.asarray(r3)
        r3 = pd.DataFrame(r3, columns=['MetricValue']+pnames)

        ## R4 ##
        r4 = invariant_image_similarity_fn(in_image1.pointer,
                                            in_image2.pointer,
                                            list(thetain), 
                                            list(thetain2), 
                                            list(thetain3),
                                            local_search_iterations, 
                                            metric,
                                            scale_image, 
                                            3,
                                            txfn4)
        r4 = np.asarray(r4)
        r4 = pd.DataFrame(r4, columns=['MetricValue']+pnames)

        rmins = [np.min(r1.iloc[:,0]), np.min(r2.iloc[:,0]), np.min(r3.iloc[:,0]), np.min(r4.iloc[:,0])]
        ww = np.argmin(rmins)

        if ww == 0:
            return r1, txfn1
        elif ww == 1:
            return r2, txfn2
        elif ww == 2:
            return r3, txfn3
        elif ww == 3:
            return r4, txfn4


def convolve_image(image, kernel_image, crop=True):
    """
    Convolve one image with another

    ANTsR function: `convolveImage`

    Arguments
    ---------
    image : ANTsImage
        image to convolve

    kernel_image : ANTsImage
        image acting as kernel

    crop : boolean
        whether to automatically crop kernel_image

    Returns
    -------
    ANTsImage

    Example
    -------
    >>> import ants
    >>> fi = ants.image_reead(ants.get_ants_data('r16'))
    >>> convimg = ants.make_image( (3,3), (1,0,1,0,-4,0,1,0,1) )
    >>> convout = ants.convolve_image( fi, convimg )
    >>> convimg2 = ants.make_image( (3,3), (0,1,0,1,0,-1,0,-1,0) )
    >>> convout2 = ants.convolve_image( fi, convimg2 )
    """
    if not isinstance(image, iio.ANTsImage):
        raise ValueError('image must be ANTsImage type')
    if not isinstance(kernel_image, iio.ANTsImage):
        raise ValueError('kernel must be ANTsImage type')
    
    orig_ptype = image.pixeltype
    if image.pixeltype != 'float':
        image = image.clone('float')
    if kernel_image.pixeltype != 'float':
        kernel_image = kernel_image.clone('float')

    if crop:
        kernel_image_mask = utils.get_mask(kernel_image)
        kernel_image = utils.crop_image(kernel_image, kernel_image_mask)
        kernel_image_mask = utils.crop_image(kernel_image_mask, kernel_image_mask)
        kernel_image[kernel_image_mask==0] = kernel_image[kernel_image_mask==1].mean()

    convolve_image_fn = lib.__dict__[_convolve_image_dict[image.dimension]]
    conv_itk_image = convolve_image_fn(image.pointer, kernel_image.pointer)
    conv_ants_image = iio.ANTsImage(conv_itk_image)

    if orig_ptype != 'float':
        conv_ants_image = conv_ants_image.clone(orig_ptype)

    return conv_ants_image




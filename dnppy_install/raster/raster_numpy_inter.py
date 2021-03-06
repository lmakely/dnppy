# local imports
from .figures import *
from .grab_data_info import *
from .null_values import *
from .project_resample import *
from .raster_clipping import *
from .raster_enforcement import *
from .raster_overlap import *
from .raster_stack import *
from .raster_statistics import *
from .temporal_fill import *


__all__=['to_numpy',            # complete
         'from_numpy']          # complete



def to_numpy(raster, num_type = False):

    """
    Wrapper for arcpy.RasterToNumpyArray with better metadata handling
    
     This is just a wraper for the RasterToNumPyArray function within arcpy, but it also
     extracts out all the spatial referencing information that will probably be needed
     to save the raster after desired manipulations have been performed.
     also see raster.from_numpy function in this module.

     inputs:
       Raster              Any raster suported by the arcpy.RasterToNumPyArray function
       num_type            must be a string equal to any of the types listed at the following
                           address [http://docs.scipy.org/doc/numpy/user/basics.types.html]
                           for example: 'uint8' or 'int32' or 'float32'
     outputs:
       numpy_rast          the numpy array version of the input raster
       Metadata            An object with the following attributes.
           .Xmin            the left edge
           .Ymin            the bottom edge
           .Xmax            the right edge
           .Ymax            the top edge
           .Xsize           the number of columns
           .Ysize           the number of rows
           .cellWidth       resolution in x direction
           .cellHeight      resolution in y direction
           .projection      the projection information to give the raster
           .NoData_Value    the numerical value which represents NoData in this raster

     Usage example:
       call this function with  " rast,Metadata = to_numpy(Raster) "
       perform numpy manipulations as you please
       then save the array with " raster.from_numpy(rast,Metadata,output)   "
    """

    # create a metadata object and assign attributes to it
    class metadata:

        def __init__(self, raster, xs, ys):

            self.Xsize          = xs
            self.Ysize          = ys
            
            self.cellWidth      = arcpy.Describe(raster).meanCellWidth
            self.cellHeight     = arcpy.Describe(raster).meanCellHeight
            
            self.Xmin           = arcpy.Describe(raster).Extent.XMin
            self.Ymin           = arcpy.Describe(raster).Extent.YMin
            self.Xmax           = self.Xmin + (xs * self.cellWidth)
            self.Ymax           = self.Ymin + (ys * self.cellHeight)

            self.rectangle      = ' '.join([str(self.Xmin),
                                            str(self.Ymin),
                                            str(self.Xmax),
                                            str(self.Ymax)])
            
            self.projection     = arcpy.Describe(raster).spatialReference
            self.NoData_Value   = arcpy.Describe(raster).noDataValue
            return

    # read in the raster as an array
    if is_rast(raster):

        numpy_rast  = arcpy.RasterToNumPyArray(raster)
        ys, xs      = numpy_rast.shape
        meta        = metadata(raster, xs, ys)
        
        if num_type:
            numpy_rast = numpy_rast.astype(num_type)
            
    else:  
        print("Raster '{0}'does not exist".format(raster))

    return numpy_rast, meta



def from_numpy(numpy_rast, Metadata, outpath, NoData_Value = False, num_type = False):
    """
    Wrapper for arcpy.NumPyArrayToRaster function with better metadata handling
    
     this is just a wraper for the NumPyArrayToRaster function within arcpy. It is used in
     conjunction with to_numpy to streamline reading image files in and out of numpy
     arrays. It also ensures that all spatial referencing and projection info is preserved
     between input and outputs of numpy manipulations.

     inputs:
       numpy_rast          the numpy array version of the input raster
       Metadata            The variable exactly as output from "to_numpy"
       outpath             output filepath of the individual raster
       NoData_Value        the no data value of the output raster
       num_type            must be a string equal to any of the types listed at the following
                           address [http://docs.scipy.org/doc/numpy/user/basics.types.html]
                           for example: 'uint8' or 'int32' or 'float32'

     Usage example:
       call to_numpy with  "rast,Metadata = to_numpy(Raster)"
       perform numpy manipulations as you please
       then save the array with "raster.from_numpy(rast, Metadata, output)"
    """

    if num_type:
        numpy_rast = numpy_rast.astype(num_type)

    if not NoData_Value:
        NoData_Value = Metadata.NoData_Value
            
    llcorner = arcpy.Point(Metadata.Xmin, Metadata.Ymin)
    
    # save the output.
    OUT = arcpy.NumPyArrayToRaster(numpy_rast, llcorner, Metadata.cellWidth ,Metadata.cellHeight)
    OUT.save(outpath)

    # define its projection
    try:
        arcpy.DefineProjection_management(outpath, Metadata.projection)
    except:
        pass

    # reset the NoData_Values
    try:
        arcpy.SetRasterProperties_management(outpath, data_type="#", nodata = "1 " + str(NoData_Value))
    except:
        pass
    
    # do statistics and pyramids
    arcpy.CalculateStatistics_management(outpath)
    arcpy.BuildPyramids_management(outpath)
    
    print("Saved output file as {0}".format(outpath))

    return





def degree_days(T_base, Max, Min, NoData_Value, outpath = False, roof = False, floor = False):

    """
    Inputs rasters for maximum and minimum temperatures, calculates Growing Degree Days
    
     this function is built to perform the common degree day calculation on either a pair
     of raster filepaths, a pair of numpy arrays, or a pair of lists. It requires, at minimum
     A maximum temperature value, a minimum temperature value, and a base temperature.
     This equation could also be used to calculate Chill hours or anything similar. 

     The equation is as follows:
                                   [(Max+Min)/2 + T_base]

     where values in Max which are greater than roof are set equal to roof
     where values in Min which are lesser than floor are set equal to floor
     consult [https://en.wikipedia.org/wiki/Growing_degree-day] for more information.

     Inputs:
       T_base          base temperature to ADD, be mindful of sign convention.
       Max             filepath, numpy array, or list of maximum temperatures
       Min             filepath, numpy array, or list of minimum temperatures
       NoData_Value    values to ignore (must be int or float)
       outpath         filepath to which output should be saved. Only works if Max and Min inputs
                       are raster filepaths with spatial referencing.
       roof            roof value above which Max temps do not mater
       floor           floor value below which Min temps do not mater
       Quiet           Set True to supress output

     Outputs:
       degree_days     numpy array of output values. This same data is saved if outpath is
                       not left at its default value of False.
    """

    # format numerical inputs as floating point values
    T_base = float(T_base)
    if roof:  roof  = float(roof)
    if floor: floor = float(floor)

    # Determine the type of input and convert to useful format for calculation
    # acceptable input formats are filepaths to rasters, numpy arrays, or lists.
    if type(Max) is list and type(Min) is list:
        
        # if the first entry in a list is a string, asume it is a filename that has
        # been placed into a list.
        if type(Max[0]) is str and type(Min[0]) is str:
            Max = Max[0]
            Min = Min[0]

            # load in the min and max files.
            highs, meta = raster.to_numpy(Max)
            lows, meta  = raster.to_numpy(Min)

            print 'Found spatialy referenced image pair!'
        else:
            highs = numpy.array(Max)
            lows  = numpy.array(Min)
            
    # if they are already numpy arrays
    elif type(Max) is numpy.ndarray:
            highs=Max
            lows =Min
            
# Begin to perform the degree day calculations.....................

    # apply roof and floor corrections if they have been specified
    if roof:  highs[highs >= roof] = roof
    if floor: lows[lows <=floor] = floor

    # find the shapes of high and low arrays
    xsh,ysh=highs.shape
    xsl,ysl=lows.shape

    # only continue if min and max arrays have the same shape
    if xsh==xsl and ysh==ysl:
        
        # set empty degree day matrix
        degree_days = numpy.zeros((xsh,ysh))
        
        # peform the calculation
        for x in range(xsh):
            for y in range(ysh):
                if round(highs[x,y]/NoData_Value,10) !=1 and round(lows[x,y]/NoData_Value,10) != 1:
                    degree_days[x,y]=((highs[x,y] + lows[x,y])/2) + T_base
                else:
                    degree_days[x,y]=NoData_Value
                
    # print error if the arrays are not the same size
    else:
        print 'Images are not the same size!, Check inputs!'
        return(False)

    # if an output path was specified, save it with the spatial referencing information.
    if outpath and type(Max) is str and type(Min) is str:
        raster.from_numpy(degree_days, meta, outpath)
        'Output saved at : ' + outpath
        
    return(degree_days)


def degree_days_accum(rasterlist, critical_values = False, outdir = False):

    """
    Accumulates degree days in a time series rasterlist
    
     This function is the logical successor to calc.degree_days. Input a list of rasters
     containing daily data to be accumulated. Output raster for a given day will be the sum
     total of the input raster for that day and all preceding days. The last output raster in
     a years worth of data (image 356) would be the sum of all 365 images. The 25th output
     raster would be a sum of the first 25 days.
     Critical value rasters will also be created. Usefull for example: we wish to know on what day
     of our 365 day sequence every pixel hits a value of 100. Input 100 as a critical value
     and that output raster will be generated. 

     Inputs:
       rasterlist          list of files, or directory containing rasters to accumulate
       critical_values     Values at which the user wishes to know WHEN the total accumulation
                           value reaches this point. For every critical value, an output
                           raster will be created. This raster contains integer values denoting
                           the index number of the file at which the value was reached.
                           This input must be a list of ints or floats, not strings.
       outdir              Desired output directory for all output files.
    """

    rasterlist = core.enf_rastlist(rasterlist)
    
    if critical_values:
        critical_values = core.enf_list(critical_values)

    # critical values of zero are problematic, so replace it with a small value.
    if 0 in critical_values:
        critical_values.remove(0)
        critical_values.append(0.000001)
        
    if outdir and not os.path.exists(outdir):
        os.makedirs(outdir)

    for i,raster in enumerate(rasterlist):

        image, meta = raster.to_numpy(raster,"float32")
        xs, ys = image.shape

        if i==0:
            Sum  = numpy.zeros((xs,ys))
            Crit = numpy.zeros((len(critical_values),xs,ys))
        
        if image.shape == Sum.shape:

            # only bother to proceed if at least one pixel is positive
            if numpy.max(image) >= 0:
                for x in range(xs):
                    for y in range(ys):

                        if image[x,y] >= 0:
                            Sum[x,y] = Sum[x,y]+image[x,y]

                        if critical_values:    
                            for z,critical_value in enumerate(critical_values):
                                if Sum[x,y] >= critical_value and Crit[z,x,y]==0:
                                    Crit[z,x,y] = i
        else:
            print "Encountered an image of incorrect size! Skipping it!"

        Sum     = Sum.astype('float32')
        outname = core.create_outname(outdir, raster, "Accum")
        raster.from_numpy(Sum, meta, outname)

        del image

    # output critical accumulation rasters.
    Crit = Crit.astype('int16')
    crit_meta = meta
    crit_meta.NoData_Value = 0
    head , tail = os.path.split(outname)        # place these in the last raster output location
    for z, critical_value in enumerate(critical_values): 
        outname = os.path.join(head,"Crit_Accum_Index_Val-{0}.tif".format(str(critical_value)))
        print "Saving :",outname
        raster.from_numpy(Crit[z,:,:], crit_meta, outname)
                     
    return

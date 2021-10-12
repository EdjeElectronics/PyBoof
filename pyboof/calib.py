from pyboof.image import *
from pyboof.ip import *
from pyboof.recognition import *
from pyboof.geo import real_nparray_to_ejml32
from abc import ABCMeta, abstractmethod
from typing import Mapping, List


class CameraModel:
    __metaclass__ = ABCMeta

    @abstractmethod
    def load(self, file_name: str):
        pass

    @abstractmethod
    def save(self, file_name: str):
        pass

    @abstractmethod
    def set_from_boof(self, boof_intrinsic):
        pass

    @abstractmethod
    def convert_to_boof(self, storage=None):
        pass


# TODO Turn this into JavaConfig instead?
class CameraPinhole(CameraModel):
    """
    BoofCV Intrinsic Camera parameters
    """

    def __init__(self, java_object=None):
        if java_object is None:
            # Intrinsic calibration matrix
            self.fx = 0
            self.fy = 0
            self.skew = 0
            self.cx = 0
            self.cy = 0
            # image shape
            self.width = 0
            self.height = 0
        else:
            self.set_from_boof(java_object)

    def load(self, file_name: str):
        """
        Loads BoofCV formatted intrinsic parameters with radial distortion from a yaml file

        :param file_name: Path to yaml file
        :return: this class
        """
        file_path = os.path.abspath(file_name)
        boof_intrinsic = gateway.jvm.boofcv.io.calibration.CalibrationIO.load(file_path)

        if boof_intrinsic is None:
            raise RuntimeError("Can't load intrinsic parameters")

        self.set_from_boof(boof_intrinsic)
        return self

    def save(self, file_name):
        file_path = os.path.abspath(file_name)
        java_obj = self.convert_to_boof()
        gateway.jvm.boofcv.io.calibration.CalibrationIO.save(java_obj, file_path)

    def set_matrix(self, fx: float, fy: float, skew: float, cx: float, cy: float):
        self.fx = fx
        self.fy = fy
        self.skew = skew
        self.cx = cx
        self.cy = cy

    def set_image_shape(self, width: int, height: int):
        self.width = width
        self.height = height

    def set(self, orig):
        self.fx = orig.fx
        self.fy = orig.fy
        self.skew = orig.skew
        self.cx = orig.cx
        self.cy = orig.cy
        self.width = orig.width
        self.height = orig.height

    def set_from_boof(self, boof_intrinsic):
        self.fx = boof_intrinsic.getFx()
        self.fy = boof_intrinsic.getFy()
        self.cx = boof_intrinsic.getCx()
        self.cy = boof_intrinsic.getCy()
        self.skew = boof_intrinsic.getSkew()
        self.width = boof_intrinsic.getWidth()
        self.height = boof_intrinsic.getHeight()

    def convert_to_boof(self, storage=None):
        if storage is None:
            boof_intrinsic = gateway.jvm.boofcv.struct.calib.CameraPinholeBrown()
        else:
            boof_intrinsic = storage
        boof_intrinsic.setFx(float(self.fx))
        boof_intrinsic.setFy(float(self.fy))
        boof_intrinsic.setCx(float(self.cx))
        boof_intrinsic.setCy(float(self.cy))
        boof_intrinsic.setSkew(float(self.skew))
        boof_intrinsic.setWidth(int(self.width))
        boof_intrinsic.setHeight(int(self.height))
        return boof_intrinsic

    def __str__(self):
        return "Pinhole{{ fx={:f} fy={:f} skew={:f} cx={:f} cy={:f} | width={:d} height={:d}}}".format(
            self.fx, self.fy, self.skew, self.cx, self.cy, self.width, self.height)


class CameraBrown(CameraPinhole):
    """
    BoofCV Intrinsic Camera parameters
    """

    def __init__(self, java_object=None):
        CameraPinhole.__init__(self, java_object)
        if java_object is None:
            # radial distortion
            self.radial = None
            # tangential terms
            self.t1 = 0
            self.t2 = 0
        else:
            self.set_from_boof(java_object)

    def set_distortion(self, radial=None, t1=0, t2=0):
        """
        Sets distortion values

        :param radial: Radial distortion
        :type radial: [float] or None
        :param t1: Tangential distortion
        :type t1: float
        :param t2:  Tangential distortion
        :type t2: float
        """
        self.radial = radial
        self.t1 = t1
        self.t2 = t2

    def set(self, orig):
        self.fx = orig.fx
        self.fy = orig.fy
        self.skew = orig.skew
        self.cx = orig.cx
        self.cy = orig.cy
        self.width = orig.width
        self.height = orig.height
        self.radial = orig.radial
        self.t1 = orig.t1
        self.t2 = orig.t2

    def set_from_boof(self, boof_intrinsic):
        CameraPinhole.set_from_boof(self, boof_intrinsic)
        jarray = boof_intrinsic.getRadial()
        if jarray is None:
            self.radial = None
        else:
            self.radial = [float(x) for x in jarray]
        self.t1 = boof_intrinsic.getT1()
        self.t2 = boof_intrinsic.getT2()

    def convert_to_boof(self, storage=None):
        if storage is None:
            boof_intrinsic = gateway.jvm.boofcv.struct.calib.CameraPinholeBrown()
        else:
            boof_intrinsic = storage

        CameraPinhole.convert_to_boof(self, boof_intrinsic)
        if self.radial is not None:
            jarray = gateway.new_array(gateway.jvm.double, len(self.radial))
            for i in range(len(self.radial)):
                jarray[i] = self.radial[i]
            boof_intrinsic.setRadial(jarray)
        boof_intrinsic.setT1(float(self.t1))
        boof_intrinsic.setT2(float(self.t2))
        return boof_intrinsic

    def is_distorted(self):
        return (self.radial is not None) or self.t1 != 0 or self.t2 != 0

    def __str__(self):
        out = "Brown{{ fx={:f} fy={:f} skew={:f} cx={:f} cy={:f} | width={:d} height={:d} ". \
            format(self.fx, self.fy, self.skew, self.cx, self.cy, self.width, self.height)
        if self.is_distorted():
            out += " | radial=" + str(self.radial) + " t1=" + str(self.t1) + " t1=" + str(self.t2) + " }"
        else:
            out += "}}"
        return out


class CameraUniversalOmni(CameraBrown):
    def __init__(self, java_object=None):
        CameraBrown.__init__(self, java_object)
        if java_object is None:
            self.mirror_offset = 0
        else:
            self.mirror_offset = java_object.getMirrorOffset()

    def set_from_boof(self, boof_intrinsic):
        CameraBrown.set_from_boof(self, boof_intrinsic)
        self.mirror_offset = boof_intrinsic.getMirrorOffset()

    def convert_to_boof(self, storage=None):
        if storage is None:
            boof_intrinsic = gateway.jvm.boofcv.struct.calib.CameraUniversalOmni(0)
        else:
            boof_intrinsic = storage
        CameraBrown.convert_to_boof(self, boof_intrinsic)
        boof_intrinsic.setMirrorOffset(float(self.mirror_offset))
        return boof_intrinsic

    def __str__(self):
        out = "UniversalOmni{{ fx={:f} fy={:f} skew={:f} cx={:f} cy={:f} | width={:d} height={:d} | mirror={:f}". \
            format(self.fx, self.fy, self.skew, self.cx, self.cy, self.width, self.height, self.mirror_offset)
        if self.is_distorted():
            out += " | radial=" + str(self.radial) + " t1=" + str(self.t1) + " t1=" + str(self.t2) + " }"
        else:
            out += "}}"
        return out


class CameraKannalaBrandt(CameraPinhole):
    def __init__(self, java_object=None):
        CameraPinhole.__init__(self, java_object)
        if java_object is None:
            self.symmetric = []
            self.radial = []
            self.radialTrig = []
            self.tangent = []
            self.tangentTrig = []
        else:
            self.set_from_boof(java_object)

    def set_from_boof(self, boof_intrinsic):
        CameraPinhole.set_from_boof(self, boof_intrinsic)
        jsymmetric = boof_intrinsic.getSymmetric()
        jradial = boof_intrinsic.getRadial()
        jradialTrig = boof_intrinsic.getRadialTrig()
        jtangent = boof_intrinsic.getTangent()
        jtangentTrig = boof_intrinsic.getTangentTrig()

        self.symmetric = [float(x) for x in jsymmetric]
        self.radial = [float(x) for x in jradial]
        self.radialTrig = [float(x) for x in jradialTrig]
        self.tangent = [float(x) for x in jtangent]
        self.tangentTrig = [float(x) for x in jtangentTrig]

    def convert_to_boof(self, storage=None):
        if storage is None:
            boof_intrinsic = gateway.jvm.boofcv.struct.calib.CameraKannalaBrandt(len(self.symmetric), len(self.radial))
        else:
            boof_intrinsic = storage
        CameraPinhole.convert_to_boof(self, boof_intrinsic)
        boof_intrinsic.setSymmetric(python_to_java_double_array(self.symmetric))
        boof_intrinsic.setRadial(python_to_java_double_array(self.radial))
        boof_intrinsic.setRadialTrig(python_to_java_double_array(self.radialTrig))
        boof_intrinsic.setTangent(python_to_java_double_array(self.tangent))
        boof_intrinsic.setTangentTrig(python_to_java_double_array(self.tangentTrig))
        return boof_intrinsic

    def __str__(self):
        out = "CameraKannalaBrandt{{ fx={:f} fy={:f} skew={:f} cx={:f} cy={:f} | width={:d} height={:d}". \
            format(self.fx, self.fy, self.skew, self.cx, self.cy, self.width, self.height)
        out += " | symmetric=" + str(self.symmetric) + " radial=" + str(self.radial) + " radialTrig=" + \
               str(self.radialTrig) + " tangent=" + str(self.tangent) + " tangentTrig=" + str(self.tangentTrig) + " }}"
        return out


class StereoParameters(CameraModel):
    """
    Stereo intrinsic and extrinsic parameters
    """

    def __init__(self, java_object=None):
        if java_object is None:
            self.left = CameraBrown()
            self.right = CameraBrown()
            self.right_to_left = Se3_F64()
        else:
            self.set_from_boof(java_object)

    def load(self, file_name: str):
        file_path = os.path.abspath(file_name)
        boof_parameters = gateway.jvm.boofcv.io.calibration.CalibrationIO.load(file_path)

        if boof_parameters is None:
            raise RuntimeError("Can't load stereo parameters")
        self.set_from_boof(boof_parameters)

    def save(self, file_name: str):
        file_path = os.path.abspath(file_name)
        java_obj = self.convert_to_boof()
        gateway.jvm.boofcv.io.calibration.CalibrationIO.save(java_obj, file_path)

    def set_from_boof(self, boof_parameters):
        self.left = CameraBrown(boof_parameters.left)
        self.right = CameraBrown(boof_parameters.right)
        self.right_to_left = Se3_F64(boof_parameters.right_to_left)

    def convert_to_boof(self, storage=None):
        if storage is None:
            boof_parameters = gateway.jvm.boofcv.struct.calib.StereoParameters()
            # In BoofCV 0.40 StereoParameters will not be initialized with null and this will not be needed
            boof_parameters.setLeft(CameraBrown().convert_to_boof())
            boof_parameters.setRight(CameraBrown().convert_to_boof())
            boof_parameters.setRightToLeft(Se3_F64().java_obj)
        else:
            boof_parameters = storage
        self.left.convert_to_boof(boof_parameters.left)
        self.right.convert_to_boof(boof_parameters.right)
        boof_parameters.right_to_left.setTo(self.right_to_left.java_obj)
        return boof_parameters

    def __str__(self):
        return "StereoParameters(left={} right={} right_to_left={})".format(self.left, self.right, self.right_to_left)


class LensNarrowDistortionFactory(JavaWrapper):
    def __init__(self, java_object, use_32=True):
        JavaWrapper.__init__(self, java_object)
        self.use_32 = use_32

    def distort(self, pixel_in, pixel_out):
        """

        :param pixel_in:
        :type pixel_in: bool
        :param pixel_out:
        :type pixel_in: bool
        :return: Point2Transform2_F32 or Point2Transform2_F64
        """
        if self.use_32:
            java_out = self.java_obj.distort_F32(pixel_in, pixel_out)
        else:
            java_out = self.java_obj.distort_F64(pixel_in, pixel_out)
        return Transform2to2(java_out)

    def undistort(self, pixel_in: bool, pixel_out: bool):
        """

        :param pixel_in:
        :type pixel_in: bool
        :param pixel_out:
        :type pixel_in: bool
        :return: Point2Transform2_F32 or Point2Transform2_F64
        """
        if self.use_32:
            java_out = self.java_obj.undistort_F32(pixel_in, pixel_out)
        else:
            java_out = self.java_obj.undistort_F64(pixel_in, pixel_out)
        return Transform2to2(java_out)


class LensWideDistortionFactory(JavaWrapper):
    def __init__(self, java_object, use_32=True):
        JavaWrapper.__init__(self, java_object)
        self.use_32 = use_32

    def distort_s_to_p(self):
        """
        Transform from unit sphere coordinates to pixel coordinates
        :return: transform
        :rtype: Transform3to2
        """
        if self.use_32:
            java_out = self.java_obj.distortStoP_F32()
        else:
            java_out = self.java_obj.distortStoP_F64()
        return Transform3to2(java_out)

    def undistort_p_to_s(self):
        """
        Transform from pixels to unit sphere coordinates
        :return: transform
        :rtype: Transform2to3
        """
        if self.use_32:
            java_out = self.java_obj.undistortPtoS_F32()
        else:
            java_out = self.java_obj.undistortPtoS_F64()
        return Transform2to3(java_out)


def create_narrow_lens_distorter(camera_model):
    """

    :param camera_model:
    :return:
    :rtype: LensNarrowDistortionFactory
    """
    if isinstance(camera_model, CameraUniversalOmni):
        raise RuntimeError("CameraUniversalOmni is not a narrow FOV camera model")
    elif isinstance(camera_model, CameraPinhole):
        boof_model = camera_model.convert_to_boof()
        java_obj = gateway.jvm.boofcv.alg.distort.pinhole.LensDistortionPinhole(boof_model)
    elif isinstance(camera_model, CameraBrown):
        boof_model = camera_model.convert_to_boof()
        if camera_model.is_distorted():
            java_obj = gateway.jvm.boofcv.alg.distort.brown.LensDistortionBrown(boof_model)
        else:
            java_obj = gateway.jvm.boofcv.alg.distort.pinhole.LensDistortionPinhole(boof_model)
    else:
        raise RuntimeError("Unknown camera model {}".format(type(camera_model)))

    return LensNarrowDistortionFactory(java_obj)


def create_wide_lens_distorter(camera_model):
    """

    :param camera_model:
    :return:
    :rtype: LensWideDistortionFactory
    """
    if isinstance(camera_model, CameraUniversalOmni):
        boof_model = camera_model.convert_to_boof()
        java_obj = gateway.jvm.boofcv.alg.distort.universal.LensDistortionUniversalOmni(boof_model)
    elif isinstance(camera_model, CameraKannalaBrandt):
        boof_model = camera_model.convert_to_boof()
        java_obj = gateway.jvm.boofcv.alg.distort.kanbra.LensDistortionKannalaBrandt(boof_model)
    else:
        raise RuntimeError("Unknown camera model {}".format(type(camera_model)))

    return LensWideDistortionFactory(java_obj)


class NarrowToWideFovPtoP(JavaWrapper):
    """
    Distortion for converting an image from a wide FOV camera (e.g. fisheye) into a narrow FOV camera (e.g. pinhole)
    Mathematically it performs a conversion from pixels in the narrow camera to the wide camera.  The center of
    focus for the narrow camera can be changed by rotating the view by invoking set_rotation_wide_to_narrow().

    """

    def __init__(self, narrow_model, wide_model):
        """
        Constructor where camera models are specified

        :param narrow_model: Camera model for narrow FOV camera
        :type narrow_model: CameraModel
        :param wide_model: Camera model for wide FOV camera
        :type wide_model: CameraModel
        """
        narrow_distort = create_narrow_lens_distorter(narrow_model)
        wide_distort = create_wide_lens_distorter(wide_model)
        java_object = gateway.jvm.boofcv.alg.distort.NarrowToWidePtoP_F32(narrow_distort.java_obj,
                                                                          wide_distort.java_obj)
        JavaWrapper.__init__(self, java_object)

    def set_rotation_wide_to_narrow(self, rotation_matrix):
        """
        Used to change the principle axis of the narrow FOC camera by rotating the view

        :param rotation_matrix: 3D rotation matrix
        :return:
        """
        self.java_obj.setRotationWideToNarrow(real_nparray_to_ejml32(rotation_matrix))
        pass

    def create_image_distort(self, image_type, border_type=Border.ZERO):
        """

        :param image_type:
        :type image_type: ImageType
        :param border_type:
        :type border_type: Border
        :return: The image distort based on this transformation
        :rtype: ImageDistort
        """
        java_image_type = image_type.java_obj
        java_interp = FactoryInterpolation(image_type).bilinear(border_type=border_type)

        java_alg = gateway.jvm.boofcv.factory.distort.FactoryDistort.distort(False, java_interp, java_image_type)
        java_pixel_transform = gateway.jvm.boofcv.struct.distort.PointToPixelTransform_F32(self.java_obj)
        java_alg.setModel(java_pixel_transform)
        return ImageDistort(java_alg)


class AdjustmentType:
    NONE = 0
    FULL_VIEW = 1
    EXPAND = 2


def adjustment_to_java(value):
    if value == AdjustmentType.NONE:
        return gateway.jvm.boofcv.alg.distort.AdjustmentType.valueOf("NONE")
    elif value == AdjustmentType.FULL_VIEW:
        return gateway.jvm.boofcv.alg.distort.AdjustmentType.valueOf("FULL_VIEW")
    elif value == AdjustmentType.EXPAND:
        return gateway.jvm.boofcv.alg.distort.AdjustmentType.valueOf("EXPAND")
    else:
        raise RuntimeError("Unknown type")


def remove_distortion(input, output, intrinsic, adjustment=AdjustmentType.FULL_VIEW, border=Border.ZERO):
    """
    Removes lens distortion from the input image and saves it into the output image. More specifically,
    it adjusts the camera model such that the radian and tangential distortion is zero. The modified
    camera model is returned.

    :param input: Java BoofCV Image
    :type input:
    :param output: Java BoofCV Image
    :type output:
    :param intrinsic: Camera model
    :type intrinsic: CameraPinhole
    :param adjustment: Should the camera model be adjusted to ensure the whole image can be seen?
    :type adjustment: AdjustmentType
    :param border: Border How should pixels outside the image border be handled?
    :type border: Border
    :return: The new camera model
    :rtype: CameraPinhole
    """
    image_type = ImageType(input.getImageType())
    desired = CameraPinhole()
    desired.set(intrinsic)
    desired.radial = [0, 0]
    desired.t1 = desired.t2 = 0

    distorter, intrinsic_out = create_change_camera_model(intrinsic, desired, image_type, adjustment, border)
    distorter.apply(input, output)
    return intrinsic_out


def create_change_camera_model(intrinsic_orig, intrinsic_desired, image_type,
                               adjustment=AdjustmentType.FULL_VIEW, border=Border.ZERO):
    """
    Creates an ImageDistort that converts an image from the original camera model to the desired camera model
    after adjusting the view to ensure that it meets the requested visibility requirements.

    :param intrinsic_orig: Original camera model prior to distortion
    :type intrinsic_orig: CameraPinhole
    :param intrinsic_desired: The desired new camera model
    :type intrinsic_desired: CameraPinhole
    :param image_type: Type of input image
    :type image_type: ImageType
    :param adjustment: Should the camera model be adjusted to ensure the whole image can be seen?
    :type adjustment: AdjustmentType
    :param border: Border How should pixels outside the image border be handled?
    :type border: Border
    :return: Distortion for removing the camera model and the new camera parameters
    :rtype: (ImageDistort,CameraPinhole)
    """

    java_image_type = image_type.get_java_object()
    java_adjustment = adjustment_to_java(adjustment)
    java_border = border_to_java(border)
    java_original = intrinsic_orig.convert_to_boof()
    java_desired = intrinsic_desired.convert_to_boof()
    java_intrinsic_out = gateway.jvm.boofcv.struct.calib.CameraPinholeBrown()
    id = gateway.jvm.boofcv.alg.distort.LensDistortionOps.changeCameraModel(
        java_adjustment, java_border, java_original, java_desired, java_intrinsic_out, java_image_type)
    return (ImageDistort(id), CameraPinhole(java_intrinsic_out))


def convert_from_boof_calibration_observations(jobservations):
    # TODO For Boof 0.29 and beyond use accessors instead
    jlist = JavaWrapper(jobservations).points
    output = []
    for o in jlist:
        output.append((o.getIndex(), o.getX(), o.getY()))
    return output


def convert_into_boof_calibration_observations(observations):
    width = int(observations["width"])
    height = int(observations["height"])
    pixels = observations["pixels"]
    jobs = gateway.jvm.boofcv.alg.geo.calibration.CalibrationObservation(width, height)
    for o in pixels:
        p = gateway.jvm.georegression.struct.point.Point2D_F64(float(o[1]), float(o[2]))
        jobs.add(p, int(o[0]))
        # TODO use this other accessor after 0.30
        # jobs.add(float(o[1]),float(o[2]),int(o[0]))

    return jobs


def calibrate_brown(observations: List, detector, num_radial=2, tangential=True, zero_skew=True):
    """
    Calibrates a Brown camera

    :param observations: List of {"points":(boofcv detections),"width":(image width),"height":(image height)}
    :param detector:
    :param num_radial:
    :param tangential:
    :param zero_skew:
    :return:
    """
    jlayout = detector.java_obj.getLayout()
    jcalib_planar = gateway.jvm.boofcv.abst.geo.calibration.CalibrateMonoPlanar(jlayout)
    jcalib_planar.configurePinhole(zero_skew, int(num_radial), tangential)
    for o in observations:
        jcalib_planar.addImage(convert_into_boof_calibration_observations(o))

    intrinsic = CameraBrown(jcalib_planar.process())

    errors = []
    for jerror in jcalib_planar.getErrors():
        errors.append({"mean": jerror.getMeanError(),
                       "max_error": jerror.getMaxError(),
                       "bias_x": jerror.getBiasX(), "bias_y": jerror.getBiasY()})

    return (intrinsic, errors)


def calibrate_universal(observations: List, detector, num_radial=2, tangential=True, zero_skew=True,
                        mirror_offset=None):
    """
    Calibrate a fisheye camera using Universal Omni model.

    :param observations: List of {"points":(boofcv detections),"width":(image width),"height":(image height)}
    :param detector:
    :param num_radial:
    :param tangential:
    :param zero_skew:
    :param mirror_offset: If None it will be estimated. 0.0 = pinhole camera. 1.0 = fisheye
    :return: (intrinsic, errors)
    """
    jlayout = detector.java_obj.getLayout()
    jcalib_planar = gateway.jvm.boofcv.abst.geo.calibration.CalibrateMonoPlanar(jlayout)
    if mirror_offset is None:
        jcalib_planar.configureUniversalOmni(zero_skew, int(num_radial), tangential)
    else:
        jcalib_planar.configureUniversalOmni(zero_skew, int(num_radial), tangential, float(mirror_offset))
    for o in observations:
        jcalib_planar.addImage(convert_into_boof_calibration_observations(o))

    intrinsic = CameraUniversalOmni(jcalib_planar.process())

    errors = []
    for jerror in jcalib_planar.getErrors():
        errors.append({"mean": jerror.getMeanError(),
                       "max_error": jerror.getMaxError(),
                       "bias_x": jerror.getBiasX(), "bias_y": jerror.getBiasY()})

    return (intrinsic, errors)


def calibrate_kannala_brandt(observations: List, detector: FiducialCalibrationDetector, num_symmetric: int = 5,
                             num_asymmetric: int = 0, zero_skew: bool = True):
    """
    Calibrate a fisheye camera using Kannala-Brandt model.

    :param observations: List of {"points":(boofcv detections),"width":(image width),"height":(image height)}
    :param detector:
    :param num_symmetric:
    :param num_asymmetric:
    :param zero_skew:
    :param mirror_offset: If None it will be estimated. 0.0 = pinhole camera. 1.0 = fisheye
    :return: (intrinsic, errors)
    """
    jlayout = detector.java_obj.getLayout()
    jcalib_planar = gateway.jvm.boofcv.abst.geo.calibration.CalibrateMonoPlanar(jlayout)
    jcalib_planar.configureKannalaBrandt(zero_skew, num_symmetric, num_asymmetric)

    for o in observations:
        jcalib_planar.addImage(convert_into_boof_calibration_observations(o))

    intrinsic = CameraKannalaBrandt(jcalib_planar.process())

    errors = []
    for jerror in jcalib_planar.getErrors():
        errors.append({"mean": jerror.getMeanError(),
                       "max_error": jerror.getMaxError(),
                       "bias_x": jerror.getBiasX(), "bias_y": jerror.getBiasY()})

    return (intrinsic, errors)


def calibrate_stereo(observations_left: List, observations_right: List, detector: FiducialCalibrationDetector,
                     num_radial: int = 4, tangential: bool = False, zero_skew: bool = True) -> (StereoParameters, List):
    """
    Calibrates a stereo camera using a Brown camera model

    :param observations: List of {"points":(boofcv detections),"width":(image width),"height":(image height)}
    :param detector:
    :param num_radial:
    :param tangential:
    :param zero_skew:
    :return:
    """
    jlayout = detector.java_obj.getLayout(0) # Hard coded for a single target
    jcalib_planar = gateway.jvm.boofcv.abst.geo.calibration.CalibrateStereoPlanar(jlayout)
    jcalib_planar.configure(zero_skew, int(num_radial), tangential)

    for idx in range(len(observations_left)):
        jobs_left = convert_into_boof_calibration_observations(observations_left[idx])
        jobs_right = convert_into_boof_calibration_observations(observations_right[idx])
        jcalib_planar.addPair(jobs_left, jobs_right)

    stereo_parameters = StereoParameters(jcalib_planar.process())

    errors = []
    for jerror in jcalib_planar.computeErrors():
        errors.append({"mean": jerror.getMeanError(),
                       "max_error": jerror.getMaxError(),
                       "bias_x": jerror.getBiasX(), "bias_y": jerror.getBiasY()})

    return (stereo_parameters, errors)

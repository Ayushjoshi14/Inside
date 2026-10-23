import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:image_picker/image_picker.dart';
import '../core/network/api_client.dart';
import '../core/utils/image_quality_checker.dart';
import '../models/scan_result_model.dart';
import 'auth_service.dart';

enum ScanStep { idle, capturing, checkingQuality, performingOcr, analyzing, complete, error }

class ScannerService extends ChangeNotifier {
  final ApiClient _apiClient = ApiClient();
  final AuthService _authService;
  final ImagePicker _picker = ImagePicker();

  ScanStep _step = ScanStep.idle;
  String _statusMessage = '';
  File? _currentImage;
  String? _extractedText;
  ScanResult? _lastResult;
  String? _errorMessage;

  ScanStep get step => _step;
  String get statusMessage => _statusMessage;
  File? get currentImage => _currentImage;
  String? get extractedText => _extractedText;
  ScanResult? get lastResult => _lastResult;
  String? get errorMessage => _errorMessage;

  ScannerService(this._authService);

  void reset() {
    _step = ScanStep.idle;
    _statusMessage = '';
    _currentImage = null;
    _extractedText = null;
    _errorMessage = null;
    notifyListeners();
  }

  /// Take a photo using camera
  Future<File?> pickFromCamera() async {
    try {
      final XFile? photo = await _picker.pickImage(
        source: ImageSource.camera,
        maxWidth: 1920,
        maxHeight: 1080,
        imageQuality: 88,
      );
      if (photo != null) {
        _currentImage = File(photo.path);
        notifyListeners();
        return _currentImage;
      }
    } catch (e) {
      _errorMessage = "Camera permission denied or camera not available.";
      notifyListeners();
    }
    return null;
  }

  /// Choose a photo from gallery using Android system Photo Picker
  Future<File?> pickFromGallery() async {
    try {
      final XFile? image = await _picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 1920,
        maxHeight: 1080,
        imageQuality: 88,
      );
      if (image != null) {
        _currentImage = File(image.path);
        notifyListeners();
        return _currentImage;
      }
    } catch (e) {
      _errorMessage = "Failed to open photo picker.";
      notifyListeners();
    }
    return null;
  }

  /// Analyzes an image or raw text
  Future<ScanResult?> processImageAndAnalyze({
    File? imageFile,
    String? directOcrText,
    String? productName,
    String? productCategory,
  }) async {
    _errorMessage = null;

    // 1. Check quality if file provided
    final file = imageFile ?? _currentImage;
    if (file != null) {
      _step = ScanStep.checkingQuality;
      _statusMessage = "Checking image clarity...";
      notifyListeners();

      final quality = await ImageQualityChecker.evaluateImageFile(file);
      if (!quality.isAcceptable) {
        _step = ScanStep.error;
        _errorMessage = quality.issueReason ?? "Image isn't clear enough.";
        notifyListeners();
        return null;
      }
    }

    // 2. OCR Text Extraction
    _step = ScanStep.performingOcr;
    _statusMessage = "Reading ingredients...";
    notifyListeners();

    // Use direct text if supplied
    String ocrText = (directOcrText ?? _extractedText ?? "").trim();
    if (ocrText.isEmpty) {
      _step = ScanStep.error;
      _errorMessage = "Please scan a clear image of the food package or ingredient label.";
      notifyListeners();
      throw UnableToIdentifyException(
        title: "Unable to Identify Product",
        message: "Please scan a clear image of the food package or ingredient label.",
      );
    }

    _extractedText = ocrText;

    // 3. Readability check on text
    final textCheck = ImageQualityChecker.evaluateTextReadability(ocrText);
    if (!textCheck.isAcceptable) {
      _step = ScanStep.error;
      _errorMessage = textCheck.issueReason;
      notifyListeners();
      throw UnableToIdentifyException(
        title: "Unable to Identify Product",
        message: textCheck.issueReason ?? "Please scan a clear image of the food package or ingredient label.",
      );
    }

    // 4. Analysis via backend / local food database
    _step = ScanStep.analyzing;
    _statusMessage = "Checking ingredients...";
    notifyListeners();

    try {
      final result = await _apiClient.analyzeText(
        ocrText,
        productName: productName,
        productCategory: productCategory,
      );
      _lastResult = result;
      _step = ScanStep.complete;
      await _authService.decrementScan();
      notifyListeners();
      return result;
    } on IncompatibleProductException catch (e) {
      _step = ScanStep.error;
      _errorMessage = e.message;
      notifyListeners();
      rethrow;
    } on UnableToIdentifyException catch (e) {
      _step = ScanStep.error;
      _errorMessage = e.message;
      notifyListeners();
      rethrow;
    } catch (e) {
      _step = ScanStep.error;
      _errorMessage = e.toString().replaceAll("Exception:", "").trim();
      notifyListeners();
      return null;
    }
  }
}

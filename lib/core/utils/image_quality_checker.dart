import 'dart:io';

class ImageQualityResult {
  final bool isAcceptable;
  final String? issueReason;

  ImageQualityResult({required this.isAcceptable, this.issueReason});
}

class ImageQualityChecker {
  /// Evaluates whether the captured or selected image meets minimum criteria
  /// for ingredient text extraction.
  static Future<ImageQualityResult> evaluateImageFile(File file) async {
    try {
      final exists = await file.exists();
      if (!exists) {
        return ImageQualityResult(
          isAcceptable: false,
          issueReason: "Image file could not be accessed.",
        );
      }

      final length = await file.length();
      // If file is unreasonably small (< 10 KB), it's likely corrupt or completely empty
      if (length < 10 * 1024) {
        return ImageQualityResult(
          isAcceptable: false,
          issueReason: "Image resolution is too low to clearly read text.",
        );
      }

      return ImageQualityResult(isAcceptable: true);
    } catch (e) {
      return ImageQualityResult(
        isAcceptable: false,
        issueReason: "Failed to verify image quality.",
      );
    }
  }

  /// Evaluates extracted text density. If OCR detected almost no words,
  /// warn the user that the label might have been blurry or off-center.
  static ImageQualityResult evaluateTextReadability(String extractedText) {
    final clean = extractedText.trim();
    if (clean.length < 15) {
      return ImageQualityResult(
        isAcceptable: false,
        issueReason: "Image isn't clear enough or text is not visible. Make sure the ingredient list is inside the frame.",
      );
    }

    // Check if it's mostly random symbols with very few alphanumeric characters
    final alphanumericCount = clean.replaceAll(RegExp(r'[^a-zA-Z0-9]'), '').length;
    if (alphanumericCount < 10) {
      return ImageQualityResult(
        isAcceptable: false,
        issueReason: "Text appears blurry or unreadable. Try taking another picture with better lighting.",
      );
    }

    return ImageQualityResult(isAcceptable: true);
  }
}

import 'dart:io';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:image_picker/image_picker.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import '../../services/scanner_service.dart';
import '../../core/network/api_client.dart';
import '../analysis/result_screen.dart';
import '../premium/premium_paywall_screen.dart';

class ScannerScreen extends StatefulWidget {
  const ScannerScreen({super.key});

  @override
  State<ScannerScreen> createState() => _ScannerScreenState();
}

class _ScannerScreenState extends State<ScannerScreen> {
  final ImagePicker _picker = ImagePicker();

  File? _capturedImage;
  bool _isAnalyzing = false;

  Future<void> _captureIngredientLabel() async {
    try {
      final XFile? photo = await _picker.pickImage(
        source: ImageSource.camera,
        maxWidth: 1920,
        maxHeight: 1080,
        imageQuality: 90,
      );

      if (photo == null) return;

      setState(() {
        _capturedImage = File(photo.path);
      });
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Could not open camera: $e'),
        ),
      );
    }
  }

  Future<void> _analyzeIngredients() async {
    if (_capturedImage == null) return;

    setState(() {
      _isAnalyzing = true;
    });

    try {
      // Create OCR recognizer
      final textRecognizer =
          TextRecognizer(script: TextRecognitionScript.latin);

      // Convert image to ML Kit input
      final inputImage = InputImage.fromFile(_capturedImage!);

      // Extract text
      final RecognizedText recognizedText =
          await textRecognizer.processImage(inputImage);

      await textRecognizer.close();

      final extractedText = recognizedText.text;

      if (extractedText.trim().isEmpty) {
        if (!mounted) return;
        setState(() {
          _isAnalyzing = false;
        });
        _showUnableToIdentifyDialog();
        return;
      }

      // Process and analyze with backend / food science engine
      if (!mounted) return;
      final scannerService = Provider.of<ScannerService>(context, listen: false);
      final result = await scannerService.processImageAndAnalyze(
        imageFile: _capturedImage,
        directOcrText: extractedText,
      );

      if (!mounted) return;

      setState(() {
        _isAnalyzing = false;
      });

      if (result != null && result.isCompatible) {
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => ResultScreen(result: result)),
        );
      } else {
        _showUnableToIdentifyDialog();
      }
    } on IncompatibleProductException catch (e) {
      if (!mounted) return;
      setState(() {
        _isAnalyzing = false;
      });
      _showIncompatibleProductDialog(
        title: e.title,
        message: e.message,
      );
    } on UnableToIdentifyException catch (e) {
      if (!mounted) return;
      setState(() {
        _isAnalyzing = false;
      });
      _showUnableToIdentifyDialog(
        title: e.title,
        message: e.message,
      );
    } on FreeScansExhaustedException {
      if (!mounted) return;
      setState(() {
        _isAnalyzing = false;
      });
      Navigator.of(context).push(
        MaterialPageRoute(builder: (_) => const PremiumPaywallScreen()),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isAnalyzing = false;
      });
      _showUnableToIdentifyDialog();
    }
  }

  void _showIncompatibleProductDialog({
    String title = "Incompatible Product",
    String message =
        "This doesn't appear to be a food product. Inside can analyze food ingredients and nutrition labels only. Please scan a food package or ingredient label.",
  }) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        titlePadding: const EdgeInsets.fromLTRB(24, 24, 24, 12),
        contentPadding: const EdgeInsets.symmetric(horizontal: 24),
        actionsPadding: const EdgeInsets.fromLTRB(24, 20, 24, 24),
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.red.shade50,
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.block_rounded,
                color: Colors.red,
                size: 28,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                title,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ],
        ),
        content: Text(
          message,
          style: const TextStyle(
            fontSize: 15,
            color: Colors.black87,
            height: 1.4,
          ),
        ),
        actions: [
          SizedBox(
            width: double.infinity,
            height: 48,
            child: ElevatedButton(
              style: ElevatedButton.styleFrom(
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              onPressed: () {
                Navigator.of(ctx).pop();
                _retake();
              },
              child: const Text(
                'Scan Again',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _showUnableToIdentifyDialog({
    String title = "Unable to Identify Product",
    String message =
        "Please scan a clear image of the food package or ingredient label.",
  }) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        titlePadding: const EdgeInsets.fromLTRB(24, 24, 24, 12),
        contentPadding: const EdgeInsets.symmetric(horizontal: 24),
        actionsPadding: const EdgeInsets.fromLTRB(24, 20, 24, 24),
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.amber.shade50,
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.search_off_rounded,
                color: Colors.amber,
                size: 28,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                title,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ],
        ),
        content: Text(
          message,
          style: const TextStyle(
            fontSize: 15,
            color: Colors.black87,
            height: 1.4,
          ),
        ),
        actions: [
          SizedBox(
            width: double.infinity,
            height: 48,
            child: ElevatedButton(
              style: ElevatedButton.styleFrom(
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              onPressed: () {
                Navigator.of(ctx).pop();
                _retake();
              },
              child: const Text(
                'Scan Again',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _retake() {
    setState(() {
      _capturedImage = null;
      _isAnalyzing = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: const Text(
          'Scan Ingredients',
          style: TextStyle(
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
      body: SafeArea(
        child: _capturedImage == null
            ? _buildCameraInstructions()
            : _buildCapturedImage(),
      ),
    );
  }

  Widget _buildCameraInstructions() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 280,
              height: 220,
              decoration: BoxDecoration(
                border: Border.all(
                  color: Colors.white,
                  width: 3,
                ),
                borderRadius: BorderRadius.circular(20),
              ),
              child: const Icon(
                Icons.document_scanner_outlined,
                color: Colors.white,
                size: 90,
              ),
            ),

            const SizedBox(height: 30),

            const Text(
              'Scan Ingredient Label',
              style: TextStyle(
                color: Colors.white,
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 12),

            const Text(
              'Take a clear photo of the ingredients or nutrition label on the product.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white70,
                fontSize: 15,
              ),
            ),

            const SizedBox(height: 35),

            SizedBox(
              width: double.infinity,
              height: 54,
              child: ElevatedButton.icon(
                onPressed: _captureIngredientLabel,
                icon: const Icon(Icons.camera_alt),
                label: const Text(
                  'Open Camera',
                  style: TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCapturedImage() {
    return Column(
      children: [
        Expanded(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(20),
              child: Image.file(
                _capturedImage!,
                width: double.infinity,
                fit: BoxFit.contain,
              ),
            ),
          ),
        ),

        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 20),
          child: Column(
            children: [
              SizedBox(
                width: double.infinity,
                height: 54,
                child: ElevatedButton.icon(
                  onPressed: _isAnalyzing
                      ? null
                      : _analyzeIngredients,
                  icon: _isAnalyzing
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.analytics_outlined),
                  label: Text(
                    _isAnalyzing
                        ? 'Reading Ingredients...'
                        : 'Analyze Ingredients',
                    style: const TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),

              const SizedBox(height: 10),

              SizedBox(
                width: double.infinity,
                height: 50,
                child: OutlinedButton.icon(
                  onPressed: _isAnalyzing ? null : _retake,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Retake Photo'),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
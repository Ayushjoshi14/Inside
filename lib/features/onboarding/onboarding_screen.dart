import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants/app_colors.dart';
import '../../core/storage/local_storage.dart';
import '../../services/auth_service.dart';
import '../home/home_screen.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final TextEditingController _nameController = TextEditingController(text: "Friend");
  String _selectedDiet = "NONE";
  final List<String> _selectedAvoids = [];
  final List<String> _selectedAllergens = [];

  final List<String> _commonAvoidOptions = [
    "Palm Oil",
    "High Fructose Corn Syrup",
    "Artificial Colours",
    "MSG",
    "Hydrogenated Oils",
    "Aspartame"
  ];

  final List<String> _commonAllergenOptions = [
    "Gluten / Wheat",
    "Peanuts",
    "Dairy / Milk",
    "Soy",
    "Tree Nuts",
    "Sulphites"
  ];

  void _completeOnboarding() async {
    final auth = Provider.of<AuthService>(context, listen: false);
    await auth.updatePreferences(
      name: _nameController.text.trim().isEmpty ? "Friend" : _nameController.text.trim(),
      dietPreference: _selectedDiet,
      avoidIngredients: _selectedAvoids,
      allergens: _selectedAllergens,
    );
    await LocalStorage.setFirstLaunchCompleted();

    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const MainNavigationShell()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 16),
              // App Brand Header
              Row(
                children: [
                  Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: AppColors.primary,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.qr_code_scanner_rounded, color: Colors.white, size: 20),
                  ),
                  const SizedBox(width: 10),
                  const Text(
                    "Inside",
                    style: TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.w800,
                      color: AppColors.textPrimary,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              const Text(
                "Personalize your scans",
                style: TextStyle(
                  fontSize: 26,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                  letterSpacing: -0.5,
                ),
              ),
              const SizedBox(height: 6),
              const Text(
                "Inside flags ingredients based on your diet and allergies. You can change this anytime.",
                style: TextStyle(
                  fontSize: 14,
                  color: AppColors.textSecondary,
                  height: 1.4,
                ),
              ),
              const SizedBox(height: 28),

              // Name Field
              const Text(
                "Your Name",
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textPrimary),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _nameController,
                decoration: const InputDecoration(
                  hintText: "e.g. Alex",
                ),
              ),
              const SizedBox(height: 24),

              // Diet Preference
              const Text(
                "Food Preference",
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textPrimary),
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  _dietChoiceChip("Vegetarian", "VEGETARIAN"),
                  const SizedBox(width: 8),
                  _dietChoiceChip("Vegan", "VEGAN"),
                  const SizedBox(width: 8),
                  _dietChoiceChip("No preference", "NONE"),
                ],
              ),
              const SizedBox(height: 28),

              // Ingredients to Avoid
              const Text(
                "Ingredients you want to avoid (optional)",
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textPrimary),
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: _commonAvoidOptions.map((opt) {
                  final isSelected = _selectedAvoids.contains(opt);
                  return FilterChip(
                    label: Text(opt),
                    selected: isSelected,
                    onSelected: (selected) {
                      setState(() {
                        if (selected) {
                          _selectedAvoids.add(opt);
                        } else {
                          _selectedAvoids.remove(opt);
                        }
                      });
                    },
                    selectedColor: AppColors.primaryLight,
                    checkmarkColor: AppColors.primaryDark,
                    labelStyle: TextStyle(
                      color: isSelected ? AppColors.primaryDark : AppColors.textPrimary,
                      fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                      fontSize: 13,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(20),
                      side: BorderSide(
                        color: isSelected ? AppColors.primary : AppColors.border,
                      ),
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(height: 28),

              // Allergens
              const Text(
                "Allergens or Intolerances (optional)",
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textPrimary),
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: _commonAllergenOptions.map((alg) {
                  final isSelected = _selectedAllergens.contains(alg);
                  return FilterChip(
                    label: Text(alg),
                    selected: isSelected,
                    onSelected: (selected) {
                      setState(() {
                        if (selected) {
                          _selectedAllergens.add(alg);
                        } else {
                          _selectedAllergens.remove(alg);
                        }
                      });
                    },
                    selectedColor: AppColors.primaryLight,
                    checkmarkColor: AppColors.primaryDark,
                    labelStyle: TextStyle(
                      color: isSelected ? AppColors.primaryDark : AppColors.textPrimary,
                      fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                      fontSize: 13,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(20),
                      side: BorderSide(
                        color: isSelected ? AppColors.primary : AppColors.border,
                      ),
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(height: 40),

              // Action Buttons
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: _completeOnboarding,
                  child: const Text("Get Started"),
                ),
              ),
              const SizedBox(height: 12),
              Center(
                child: TextButton(
                  onPressed: _completeOnboarding,
                  child: const Text(
                    "Skip for now",
                    style: TextStyle(
                      color: AppColors.textSecondary,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }

  Widget _dietChoiceChip(String label, String value) {
    final isSelected = _selectedDiet == value;
    return Expanded(
      child: GestureDetector(
        onTap: () {
          setState(() {
            _selectedDiet = value;
          });
        },
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: isSelected ? AppColors.primaryLight : AppColors.surface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: isSelected ? AppColors.primary : AppColors.border,
              width: isSelected ? 1.5 : 1,
            ),
          ),
          alignment: Alignment.center,
          child: Text(
            label,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 13,
              fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
              color: isSelected ? AppColors.primaryDark : AppColors.textPrimary,
            ),
          ),
        ),
      ),
    );
  }
}

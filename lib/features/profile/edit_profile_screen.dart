import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants/app_colors.dart';
import '../../services/auth_service.dart';

class EditProfileScreen extends StatefulWidget {
  const EditProfileScreen({super.key});

  @override
  State<EditProfileScreen> createState() => _EditProfileScreenState();
}

class _EditProfileScreenState extends State<EditProfileScreen> {
  late TextEditingController _nameController;
  late String _diet;
  late List<String> _avoidList;
  late List<String> _allergenList;
  final TextEditingController _customAvoidController = TextEditingController();

  final List<String> _commonAvoidOptions = [
    "Palm Oil",
    "High Fructose Corn Syrup",
    "Artificial Colours",
    "MSG",
    "Hydrogenated Oils",
    "Aspartame",
    "Carrageenan",
    "Caramel IV"
  ];

  final List<String> _commonAllergenOptions = [
    "Gluten / Wheat",
    "Peanuts",
    "Dairy / Milk",
    "Soy",
    "Tree Nuts",
    "Sulphites",
    "Egg",
    "Fish"
  ];

  @override
  void initState() {
    super.initState();
    final profile = Provider.of<AuthService>(context, listen: false).profile;
    _nameController = TextEditingController(text: profile?.name ?? 'Friend');
    _diet = profile?.dietPreference ?? 'NONE';
    _avoidList = List.from(profile?.avoidIngredients ?? []);
    _allergenList = List.from(profile?.allergens ?? []);
  }

  void _save() async {
    final auth = Provider.of<AuthService>(context, listen: false);
    await auth.updatePreferences(
      name: _nameController.text.trim(),
      dietPreference: _diet,
      avoidIngredients: _avoidList,
      allergens: _allergenList,
    );
    if (!mounted) return;
    Navigator.of(context).pop();
  }

  void _addCustomAvoid() {
    final text = _customAvoidController.text.trim();
    if (text.isNotEmpty && !_avoidList.contains(text)) {
      setState(() {
        _avoidList.add(text);
        _customAvoidController.clear();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Manage Preferences'),
        actions: [
          TextButton(
            onPressed: _save,
            child: const Text('Save', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text("Name", style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
            const SizedBox(height: 8),
            TextField(controller: _nameController),
            const SizedBox(height: 24),

            const Text("Dietary Preference", style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
            const SizedBox(height: 10),
            Row(
              children: [
                _dietOption("Vegetarian", "VEGETARIAN"),
                const SizedBox(width: 8),
                _dietOption("Vegan", "VEGAN"),
                const SizedBox(width: 8),
                _dietOption("No preference", "NONE"),
              ],
            ),
            const SizedBox(height: 28),

            const Text("Ingredients to Avoid", style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
            const SizedBox(height: 6),
            const Text("Inside will highlight these ingredients in RED as AVOID during scans.",
                style: TextStyle(fontSize: 13, color: AppColors.textSecondary)),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _commonAvoidOptions.map((opt) {
                final isSelected = _avoidList.contains(opt);
                return FilterChip(
                  label: Text(opt),
                  selected: isSelected,
                  onSelected: (selected) {
                    setState(() {
                      if (selected) {
                        _avoidList.add(opt);
                      } else {
                        _avoidList.remove(opt);
                      }
                    });
                  },
                  selectedColor: AppColors.primaryLight,
                  checkmarkColor: AppColors.primaryDark,
                );
              }).toList(),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _customAvoidController,
                    decoration: const InputDecoration(
                      hintText: "Add custom ingredient...",
                      isDense: true,
                    ),
                    onSubmitted: (_) => _addCustomAvoid(),
                  ),
                ),
                const SizedBox(width: 8),
                FilledButton(
                  onPressed: _addCustomAvoid,
                  child: const Text("Add"),
                ),
              ],
            ),
            const SizedBox(height: 28),

            const Text("Allergens", style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _commonAllergenOptions.map((alg) {
                final isSelected = _allergenList.contains(alg);
                return FilterChip(
                  label: Text(alg),
                  selected: isSelected,
                  onSelected: (selected) {
                    setState(() {
                      if (selected) {
                        _allergenList.add(alg);
                      } else {
                        _allergenList.remove(alg);
                      }
                    });
                  },
                  selectedColor: AppColors.primaryLight,
                  checkmarkColor: AppColors.primaryDark,
                );
              }).toList(),
            ),
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }

  Widget _dietOption(String label, String val) {
    final isSelected = _diet == val;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _diet = val),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10),
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
              fontSize: 12,
              fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
              color: isSelected ? AppColors.primaryDark : AppColors.textPrimary,
            ),
          ),
        ),
      ),
    );
  }
}

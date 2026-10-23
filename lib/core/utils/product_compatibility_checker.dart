enum CompatibilityStatus {
  compatible,
  incompatible,
  unreadable,
}

class ProductCompatibilityResult {
  final CompatibilityStatus status;
  final String title;
  final String message;
  final List<String> reasons;
  final bool isFood;

  const ProductCompatibilityResult({
    required this.status,
    required this.title,
    required this.message,
    required this.reasons,
    required this.isFood,
  });

  bool get isCompatible => status == CompatibilityStatus.compatible;
}

class ProductCompatibilityChecker {
  static const String incompatibleTitle = "Incompatible Product";
  static const String incompatibleMessage =
      "This doesn't appear to be a food product. Inside can analyze food ingredients and nutrition labels only. Please scan a food package or ingredient label.";

  static const String unreadableTitle = "Unable to Identify Product";
  static const String unreadableMessage =
      "Please scan a clear image of the food package or ingredient label.";

  // 1. Non-food markers
  static final List<RegExp> bookPatterns = [
    RegExp(r'\bisbn(?:-1[03])?[:\s\d\-]+', caseSensitive: false),
    RegExp(r'\bcopyright\b', caseSensitive: false),
    RegExp(r'\ball\s+rights\s+reserved\b', caseSensitive: false),
    RegExp(r'\bpublished\s+by\b', caseSensitive: false),
    RegExp(r'\bpublisher\b', caseSensitive: false),
    RegExp(r'\bchapter\s+\d+\b', caseSensitive: false),
    RegExp(r'\bpage\s+\d+\b', caseSensitive: false),
    RegExp(r'\btable\s+of\s+contents\b', caseSensitive: false),
    RegExp(r'\bauthor\b', caseSensitive: false),
    RegExp(r'\bpreface\b', caseSensitive: false),
    RegExp(r'\bforeword\b', caseSensitive: false),
    RegExp(r'\bbibliography\b', caseSensitive: false),
    RegExp(r'\bedition\b', caseSensitive: false),
    RegExp(r'\buniversity\s+press\b', caseSensitive: false),
    RegExp(r'\bpaperback\b', caseSensitive: false),
    RegExp(r'\bhardcover\b', caseSensitive: false),
    RegExp(r'\bjournal\s+of\b', caseSensitive: false),
    RegExp(r'\bvolume\s+\d+\b', caseSensitive: false),
    RegExp(r'\bprinted\s+in\b', caseSensitive: false),
    RegExp(r'\breading\s+level\b', caseSensitive: false),
    RegExp(r'\blibrary\s+of\s+congress\b', caseSensitive: false),
  ];

  static final List<RegExp> electronicsPatterns = [
    RegExp(r'\bsmartphone\b', caseSensitive: false),
    RegExp(r'\bmobile\s+phone\b', caseSensitive: false),
    RegExp(r'\bcell\s*phone\b', caseSensitive: false),
    RegExp(r'\bsamsung(?:\s+galaxy)?\b', caseSensitive: false),
    RegExp(r'\biphone\b', caseSensitive: false),
    RegExp(r'\bipad\b', caseSensitive: false),
    RegExp(r'\bqualcomm\b', caseSensitive: false),
    RegExp(r'\bsnapdragon\b', caseSensitive: false),
    RegExp(r'\b\d+\s*gb\s*ram\b', caseSensitive: false),
    RegExp(r'\b\d+\s*gb\s*(?:rom|storage)\b', caseSensitive: false),
    RegExp(r'\b\d+\s*mp\s*camera\b', caseSensitive: false),
    RegExp(r'\bmegapixel\b', caseSensitive: false),
    RegExp(r'\bamoled\b', caseSensitive: false),
    RegExp(r'\boled\b', caseSensitive: false),
    RegExp(r'\blcd(?:\s+display)?\b', caseSensitive: false),
    RegExp(r'(?<![\d.])5g\s*(?:lte|nr|network|cellular|phone|smartphone|connectivity)\b', caseSensitive: false),
    RegExp(r'\b4g\s*lte\b', caseSensitive: false),
    RegExp(r'\b\d+\s*mah\b', caseSensitive: false),
    RegExp(r'\bimei\b', caseSensitive: false),
    RegExp(r'\bbluetooth\b', caseSensitive: false),
    RegExp(r'\bwi-?fi\b', caseSensitive: false),
    RegExp(r'\btype-c\b', caseSensitive: false),
    RegExp(r'\busb(?:-c)?\b', caseSensitive: false),
    RegExp(r'\brefresh\s*rate\b', caseSensitive: false),
    RegExp(r'\bprocessor\b', caseSensitive: false),
    RegExp(r'\bandroid\s*\d+\b', caseSensitive: false),
    RegExp(r'\bios\s*\d+\b', caseSensitive: false),
    RegExp(r'\bghz\b', caseSensitive: false),
    RegExp(r'\bintel\s*core\b', caseSensitive: false),
    RegExp(r'\bdisplay\s*resolution\b', caseSensitive: false),
    RegExp(r'\bsim\s*card\b', caseSensitive: false),
    RegExp(r'\bdual\s*sim\b', caseSensitive: false),
    RegExp(r'\bcharger\b', caseSensitive: false),
    RegExp(r'\bearphone\b', caseSensitive: false),
    RegExp(r'\bheadphone\b', caseSensitive: false),
  ];

  static final List<RegExp> clothingPatterns = [
    RegExp(r'\b\d{1,3}\%\s*(?:cotton|polyester|elastane|spandex|wool|linen|nylon|rayon|silk)\b', caseSensitive: false),
    RegExp(r'\bmachine\s*wash\b', caseSensitive: false),
    RegExp(r'\bdo\s*not\s*bleach\b', caseSensitive: false),
    RegExp(r'\bhand\s*wash\b', caseSensitive: false),
    RegExp(r'\btumble\s*dry\b', caseSensitive: false),
    RegExp(r'\biron\s*low\b', caseSensitive: false),
    RegExp(r'\bdry\s*clean\b', caseSensitive: false),
    RegExp(r'\bsize\s*:\s*(?:xs|s|m|l|xl|xxl|\d{2,3})\b', caseSensitive: false),
    RegExp(r'\bapparel\b', caseSensitive: false),
    RegExp(r'\bgarment\b', caseSensitive: false),
    RegExp(r'\bshirt\b', caseSensitive: false),
    RegExp(r'\bt-shirt\b', caseSensitive: false),
    RegExp(r'\btrousers?\b', caseSensitive: false),
    RegExp(r'\bjeans\b', caseSensitive: false),
    RegExp(r'\bshoes?\b', caseSensitive: false),
    RegExp(r'\bsneakers?\b', caseSensitive: false),
  ];

  static final List<RegExp> furnitureHardwarePatterns = [
    RegExp(r'\bassembly\s+instructions\b', caseSensitive: false),
    RegExp(r'\bchoking\s+hazard\b', caseSensitive: false),
    RegExp(r'\bnot\s+suitable\s+for\s+children\b', caseSensitive: false),
    RegExp(r'\bmodel\s*(?:no|number)?[:\s\w\d\-]+', caseSensitive: false),
    RegExp(r'\b220\s*-\s*240\s*v\b', caseSensitive: false),
    RegExp(r'\b50\s*hz\b', caseSensitive: false),
    RegExp(r'\bwattage\b', caseSensitive: false),
    RegExp(r'\bwarranty\b', caseSensitive: false),
    RegExp(r'\bserial\s*(?:no|number)\b', caseSensitive: false),
    RegExp(r'\bfurniture\b', caseSensitive: false),
    RegExp(r'\bsofa\b', caseSensitive: false),
    RegExp(r'\bwardrobe\b', caseSensitive: false),
    RegExp(r'\bbookshelf\b', caseSensitive: false),
    RegExp(r'\btoy\b', caseSensitive: false),
  ];

  static final List<RegExp> medicinePatterns = [
    RegExp(r'\brx\s*(?:only)?\b', caseSensitive: false),
    RegExp(r'\bprescription\s*(?:drug|medicine|only)\b', caseSensitive: false),
    RegExp(r'\bschedule\s*[ghh1]\s*(?:drug|prescription)\b', caseSensitive: false),
    RegExp(r'\bdosage\s*:\s*(?:as\s*directed|1\s*tablet|2\s*tablets|\d+\s*mg)\b', caseSensitive: false),
    RegExp(r'\bindications?\s*[:\-\s]', caseSensitive: false),
    RegExp(r'\bcontraindications?\b', caseSensitive: false),
    RegExp(r'\bactive\s*pharmaceutical\s*ingredient\b', caseSensitive: false),
    RegExp(r'\btherapeutic\s*use\b', caseSensitive: false),
    RegExp(r'\bpharmacist\b', caseSensitive: false),
    RegExp(r'\bpharmaceuticals?\b', caseSensitive: false),
    RegExp(r'\b(?:tablets?|capsules?|syrup|injection|ointment)\s*i\.?p\.?\b', caseSensitive: false),
    RegExp(r'\bnot\s+for\s+human\s+consumption\b', caseSensitive: false),
  ];

  static final List<RegExp> cosmeticPatterns = [
    RegExp(r'\bfor\s*external\s*use\s*only\b', caseSensitive: false),
    RegExp(r'\bshampoo\b', caseSensitive: false),
    RegExp(r'\bconditioner\b', caseSensitive: false),
    RegExp(r'\bface\s*wash\b', caseSensitive: false),
    RegExp(r'\bbody\s*wash\b', caseSensitive: false),
    RegExp(r'\bsoap\s*bar\b', caseSensitive: false),
    RegExp(r'\bmoisturizer\b', caseSensitive: false),
    RegExp(r'\bsunscreen\b', caseSensitive: false),
    RegExp(r'\bbody\s*lotion\b', caseSensitive: false),
    RegExp(r'\btoothpaste\b', caseSensitive: false),
    RegExp(r'\bmouthwash\b', caseSensitive: false),
    RegExp(r'\bdeodorant\b', caseSensitive: false),
    RegExp(r'\bperfume\b', caseSensitive: false),
    RegExp(r'\bmascara\b', caseSensitive: false),
    RegExp(r'\blipstick\b', caseSensitive: false),
  ];

  // 2. Strong food markers
  static final List<RegExp> foodHeaderPatterns = [
    RegExp(r'\b(?:ingredients|ingredients\s*used|ingredients\s*list|composition)\s*[:\-\s]', caseSensitive: false),
    RegExp(r'\bcontents\s*[:\-\s]', caseSensitive: false),
    RegExp(r'\bcontains\s+added\s+flavour', caseSensitive: false),
    RegExp(r'\bcontains\s+allergens?', caseSensitive: false),
    RegExp(r'\ballergen\s+(?:advice|declaration|information)\b', caseSensitive: false),
    RegExp(r'\bmay\s+contain\s*[:\-\s]', caseSensitive: false),
  ];

  static final List<RegExp> nutritionPanelPatterns = [
    RegExp(r'\bnutrition(?:al)?\s*(?:information|facts|values?)\b', caseSensitive: false),
    RegExp(r'\bper\s*100\s*(?:g|ml)\b', caseSensitive: false),
    RegExp(r'\bper\s*serving\b', caseSensitive: false),
    RegExp(r'\benergy\s*[:\-\s]*\d+\s*(?:kcal|cal|kj)\b', caseSensitive: false),
    RegExp(r'\b(?:total\s*fat|saturated\s*fat|trans\s*fat|cholesterol|carbohydrate|total\s*sugars|added\s*sugars|dietary\s*fiber)\b', caseSensitive: false),
  ];

  static final List<RegExp> foodRegulatoryPatterns = [
    RegExp(r'\bfssai\b', caseSensitive: false),
    RegExp(r'\blic\.?\s*(?:no\.?)?\s*[:\s\d\-]+', caseSensitive: false),
    RegExp(r'\bbest\s+before\b', caseSensitive: false),
    RegExp(r'\buse\s+by\b', caseSensitive: false),
    RegExp(r'\bexp(?:iry)?\.?\s*(?:date)?\b', caseSensitive: false),
    RegExp(r'\bmfg\.?\s*(?:date)?\b', caseSensitive: false),
    RegExp(r'\bnet\s*(?:wt\.?|weight|qty|quantity)\b', caseSensitive: false),
    RegExp(r'\bstore\s+in\s+a\s+cool\b', caseSensitive: false),
    RegExp(r'\bkeep\s+refrigerated\b', caseSensitive: false),
    RegExp(r'\bveg(?:etarian)?\s+logo\b', caseSensitive: false),
  ];

  static final List<RegExp> foodAdditivePatterns = [
    RegExp(r'\b(?:ins|e)\s*\d{3,4}[a-z]?\b', caseSensitive: false),
    RegExp(r'\b(?:emulsifier|stabilizer|acidity\s*regulator|raising\s*agent|preservative|antioxidant|flavour\s*enhancer|thickener|anti-caking\s*agent|leavening\s*agent)\b', caseSensitive: false),
  ];

  static const List<String> commonBrands = [
    "Britannia", "Parle", "Amul", "Nestle", "Maggi", "Cadbury", "Lay's",
    "Haldiram", "Kurkure", "Tropicana", "Real", "Kissan", "Kellogg's",
    "Doritos", "Oreo", "Sunfeast", "Hershey's", "Epigamia", "Bournvita",
    "Mother Dairy", "Dabur", "Tata", "Saffola", "MTR", "Bikaji", "Balaji",
    "NutriChoice", "Good Day", "Marie Gold", "Monaco", "KitKat", "Snickers",
    "Sprite", "Fanta", "Thums Up", "Limca", "Maaza", "Frooti", "Bingo", "Pringles"
  ];

  static const List<String> foodSpecificItems = [
    "wheat flour", "refined wheat flour", "atta", "maida", "palm oil", "palmolein",
    "vegetable oil", "sunflower oil", "soybean oil", "mustard oil", "liquid glucose",
    "invert sugar", "cocoa solids", "cocoa butter", "cocoa powder", "milk solids",
    "skimmed milk", "whole milk", "toned milk", "iodised salt", "baking powder",
    "citric acid", "soy lecithin", "lecithin", "yeast", "semolina", "durum wheat",
    "potato flakes", "potato starch", "corn starch", "corn flour", "rice flour",
    "rolled oats", "oat flakes", "corn flakes", "mango pulp", "apple juice concentrate",
    "malt extract", "cardamom", "cinnamon", "turmeric", "cumin", "coriander powder"
  ];

  static ProductCompatibilityResult evaluate(
    String ocrText, {
    String? productName,
    String? productCategory,
  }) {
    return checkCompatibility(
      ocrText: ocrText,
      productName: productName,
      productCategory: productCategory,
    );
  }

  static ProductCompatibilityResult checkCompatibility({
    required String ocrText,
    String? productName,
    String? productCategory,
  }) {
    if (ocrText.trim().isEmpty) {
      return const ProductCompatibilityResult(
        status: CompatibilityStatus.unreadable,
        title: unreadableTitle,
        message: unreadableMessage,
        reasons: ["Image or OCR text is blank."],
        isFood: false,
      );
    }

    final cleanText = ocrText.trim();
    final alphanumericCount = cleanText.replaceAll(RegExp(r'[^a-zA-Z0-9]'), '').length;
    final words = RegExp(r'[a-zA-Z]{2,}').allMatches(cleanText).length;

    // 1. Unreadable / Gibberish Check
    if (alphanumericCount < 12 || words < 3) {
      return const ProductCompatibilityResult(
        status: CompatibilityStatus.unreadable,
        title: unreadableTitle,
        message: unreadableMessage,
        reasons: ["Text is too short or lacks readable words."],
        isFood: false,
      );
    }

    final lowerText = cleanText.toLowerCase();
    final nonFoodMatches = <String>[];

    for (final p in medicinePatterns) {
      if (p.hasMatch(cleanText)) {
        nonFoodMatches.add("pharmaceutical / medicinal marker");
      }
    }

    for (final p in cosmeticPatterns) {
      if (p.hasMatch(cleanText)) {
        nonFoodMatches.add("cosmetic / personal care marker");
      }
    }

    for (final p in bookPatterns) {
      if (p.hasMatch(cleanText)) {
        nonFoodMatches.add("book / print publication marker");
      }
    }

    for (final p in electronicsPatterns) {
      if (p.hasMatch(cleanText)) {
        nonFoodMatches.add("electronics / mobile device marker");
      }
    }

    for (final p in clothingPatterns) {
      if (p.hasMatch(cleanText)) {
        nonFoodMatches.add("clothing / apparel marker");
      }
    }

    for (final p in furnitureHardwarePatterns) {
      if (p.hasMatch(cleanText)) {
        nonFoodMatches.add("furniture / hardware marker");
      }
    }

    if (RegExp(r'\b(?:in this chapter|the author|we argue that|as discussed in|study shows that|furthermore,|moreover,)\b', caseSensitive: false).hasMatch(cleanText)) {
      nonFoodMatches.add("literary / academic prose discourse");
    }

    // Explicit non-food markers
    if (nonFoodMatches.isNotEmpty) {
      String specificTitle = incompatibleTitle;
      String specificMsg = incompatibleMessage;
      if (nonFoodMatches.any((m) => m.contains("pharmaceutical"))) {
        specificTitle = "Incompatible Product: Medicine / Drug";
        specificMsg =
            "This appears to be a medicine or pharmaceutical product. Inside is designed to analyze food and beverage products only. Please consult a doctor or pharmacist for medication details.";
      } else if (nonFoodMatches.any((m) => m.contains("cosmetic"))) {
        specificTitle = "Incompatible Product: Cosmetic / Personal Care";
        specificMsg =
            "This appears to be a cosmetic or personal care product. Inside is designed to analyze edible food and beverage products only.";
      }

      return ProductCompatibilityResult(
        status: CompatibilityStatus.incompatible,
        title: specificTitle,
        message: specificMsg,
        reasons: ["Detected non-food indicators: ${nonFoodMatches.toSet().join(', ')}"],
        isFood: false,
      );
    }

    // 2. Check for Food Evidence
    int foodEvidenceScore = 0;
    final foodEvidences = <String>[];

    if (foodHeaderPatterns.any((p) => p.hasMatch(cleanText))) {
      foodEvidenceScore += 3;
      foodEvidences.add("ingredient list header");
    }

    if (nutritionPanelPatterns.any((p) => p.hasMatch(cleanText))) {
      foodEvidenceScore += 3;
      foodEvidences.add("nutrition information panel");
    }

    final regCount = foodRegulatoryPatterns.where((p) => p.hasMatch(cleanText)).length;
    if (regCount > 0) {
      foodEvidenceScore += (regCount * 2).clamp(0, 4);
      foodEvidences.add("food packaging & regulatory markers");
    }

    final addCount = foodAdditivePatterns.where((p) => p.hasMatch(cleanText)).length;
    if (addCount > 0) {
      foodEvidenceScore += (addCount * 2).clamp(0, 3);
      foodEvidences.add("food additive & INS codes");
    }

    for (final brand in commonBrands) {
      if (RegExp('\\b${RegExp.escape(brand)}\\b', caseSensitive: false).hasMatch(cleanText)) {
        foodEvidenceScore += 2;
        foodEvidences.add("recognized food brand ($brand)");
        break;
      }
    }

    final matchedIngredients = foodSpecificItems.where((item) => lowerText.contains(item)).toList();
    if (matchedIngredients.length >= 2) {
      foodEvidenceScore += matchedIngredients.length.clamp(0, 3);
      foodEvidences.add("recognized formulation ingredients (${matchedIngredients.length} items)");
    }

    // 3. Final Compatibility Decision
    // Threshold: Must have at least 3 points of food evidence to be compatible.
    if (foodEvidenceScore >= 3) {
      return ProductCompatibilityResult(
        status: CompatibilityStatus.compatible,
        title: "Compatible Food Product",
        message: "Food product label verified.",
        reasons: foodEvidences,
        isFood: true,
      );
    }

    // Check mild non-food cues
    if (RegExp(r'\b(?:phone|laptop|cable|shirt|t-shirt|pant|shoes|toy|plastic|screw|paper|book|novel)\b', caseSensitive: false).hasMatch(cleanText)) {
      return const ProductCompatibilityResult(
        status: CompatibilityStatus.incompatible,
        title: incompatibleTitle,
        message: incompatibleMessage,
        reasons: ["Not a food product."],
        isFood: false,
      );
    }

    // Ambiguous, unclear, or insufficient food evidence
    return const ProductCompatibilityResult(
      status: CompatibilityStatus.unreadable,
      title: unreadableTitle,
      message: unreadableMessage,
      reasons: ["Insufficient evidence of a food product or ingredient label."],
      isFood: false,
    );
  }
}

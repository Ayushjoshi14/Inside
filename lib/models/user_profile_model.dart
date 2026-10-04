class UserProfile {
  final int userId;
  final String email;
  final String name;
  final String dietPreference; // 'NONE', 'VEGETARIAN', 'VEGAN'
  final List<String> avoidIngredients;
  final List<String> allergens;
  final bool isPremium;
  final int scansCount;
  final int scansLeft;

  UserProfile({
    required this.userId,
    required this.email,
    required this.name,
    this.dietPreference = 'NONE',
    this.avoidIngredients = const [],
    this.allergens = const [],
    this.isPremium = false,
    this.scansCount = 0,
    this.scansLeft = 3,
  });

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      userId: json['user_id'] ?? 0,
      email: json['email'] ?? '',
      name: json['name'] ?? 'Friend',
      dietPreference: json['diet_preference'] ?? 'NONE',
      avoidIngredients: (json['avoid_ingredients'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      allergens: (json['allergens'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      isPremium: json['is_premium'] ?? false,
      scansCount: json['scans_count'] ?? 0,
      scansLeft: json['scans_left'] ?? 3,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'user_id': userId,
      'email': email,
      'name': name,
      'diet_preference': dietPreference,
      'avoid_ingredients': avoidIngredients,
      'allergens': allergens,
      'is_premium': isPremium,
      'scans_count': scansCount,
      'scans_left': scansLeft,
    };
  }

  UserProfile copyWith({
    String? name,
    String? dietPreference,
    List<String>? avoidIngredients,
    List<String>? allergens,
    bool? isPremium,
    int? scansCount,
    int? scansLeft,
  }) {
    return UserProfile(
      userId: userId,
      email: email,
      name: name ?? this.name,
      dietPreference: dietPreference ?? this.dietPreference,
      avoidIngredients: avoidIngredients ?? this.avoidIngredients,
      allergens: allergens ?? this.allergens,
      isPremium: isPremium ?? this.isPremium,
      scansCount: scansCount ?? this.scansCount,
      scansLeft: scansLeft ?? this.scansLeft,
    );
  }
}

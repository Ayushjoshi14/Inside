# Proguard rules for Inside (Ingredient Scanner)

# Flutter Wrapper
-keep class io.flutter.app.** { *; }
-keep class io.flutter.plugin.**  { *; }
-keep class io.flutter.util.**  { *; }
-keep class io.flutter.view.**  { *; }
-keep class io.flutter.**  { *; }
-keep class io.flutter.plugins.**  { *; }

# Google ML Kit Text Recognition
-keep class com.google.mlkit.vision.text.** { *; }
-keep interface com.google.mlkit.vision.text.** { *; }
-dontwarn com.google.mlkit.vision.text.**
-keep class com.google.android.gms.vision.** { *; }
-dontwarn com.google.android.gms.vision.**

# Razorpay SDK
-keep class com.razorpay.** { *; }
-dontwarn com.razorpay.**
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}
-dontwarn com.google.android.gms.**

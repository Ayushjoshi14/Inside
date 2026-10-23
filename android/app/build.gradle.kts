import java.util.Properties
import java.io.FileInputStream
import java.io.File

plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

val keystoreProperties = Properties()
val keystorePropertiesFile: File? = listOf(
    rootProject.file("key.properties"),
    rootProject.file("../key.properties"),
    file("key.properties")
).firstOrNull { it.exists() }

val hasKeystore = keystorePropertiesFile != null
if (hasKeystore && keystorePropertiesFile != null) {
    keystoreProperties.load(FileInputStream(keystorePropertiesFile))
}

android {
    namespace = "com.ayush.inside"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        applicationId = "com.ayush.inside"
        minSdk = 24
        targetSdk = flutter.targetSdkVersion

        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    signingConfigs {
        create("release") {
            if (hasKeystore) {
                keyAlias = keystoreProperties.getProperty("keyAlias")
                keyPassword = keystoreProperties.getProperty("keyPassword")
                storePassword = keystoreProperties.getProperty("storePassword")
                val storeFilePath = keystoreProperties.getProperty("storeFile")
                if (!storeFilePath.isNullOrBlank()) {
                    val rawFile = File(storeFilePath)
                    val rootFile = rootProject.file(storeFilePath)
                    val appFile = file(storeFilePath)
                    storeFile = when {
                        rawFile.isAbsolute && rawFile.exists() -> rawFile
                        rootFile.exists() -> rootFile
                        appFile.exists() -> appFile
                        rawFile.exists() -> rawFile
                        else -> rootFile
                    }
                }
            }
        }
    }

    buildTypes {
        release {
            val isReleaseSigningConfigured = hasKeystore &&
                signingConfigs.getByName("release").storeFile?.exists() == true

            signingConfig = if (isReleaseSigningConfigured) {
                signingConfigs.getByName("release")
            } else {
                signingConfigs.getByName("debug")
            }
            isMinifyEnabled = false
            isShrinkResources = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}

tasks.matching { it.name.contains("PreBundle") || it.name.contains("packageReleaseBundle") }.configureEach {
    doFirst {
        val assetsDir = layout.buildDirectory.dir("intermediates/assets/release/mergeReleaseAssets").get().asFile
        if (!assetsDir.exists()) {
            assetsDir.mkdirs()
        }
    }
}


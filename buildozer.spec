[app]
title = Vitality Tracker
package.name = vitalitytracker
package.domain = com.vitality.app
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0.0

requirements = python3,kivy==2.3.0,requests,urllib3,certifi,charset_normalizer,idna

orientation = portrait
fullscreen = 0

# Android Architecture Targets
android.api = 33
android.minapi = 26
android.ndk = 25b
android.build_tools_version = 34.0.0
android.accept_sdk_license = True
android.archs = arm64-v8a

# Minimum required permissions
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# Security Hardening Directives
android.manifest.uses_cleartext_traffic = false
android.allow_backup = false

# Skip buggy vector graphics recipe that caused the IndexError
android.blacklist_recipes = libthorvg

# Use p4a develop branch (fixes OpenSSL, aidl, and hostpython3 build errors with NDK 25b)
p4a.branch = develop

[buildozer]
log_level = 2
warn_on_root = 1
{
  lib,
  rustPlatform,
  stdenv,
  alsa-lib,
  cacert,
  clang,
  cmake,
  copyDesktopItems,
  dbus,
  fontconfig,
  freetype,
  gnugrep,
  gst_all_1,
  krb5,
  libclang,
  libGL,
  libunwind,
  libx11,
  libxcb,
  libxcursor,
  libxfixes,
  libxinerama,
  libxkbcommon,
  libxrandr,
  makeDesktopItem,
  makeWrapper,
  nasm,
  openh264,
  openssl,
  perl,
  udev,
  pkg-config,
  vulkan-loader,
  wayland,
}:

assert lib.assertMsg stdenv.hostPlatform.isLinux
  "OxideLab's Nix package is supported only on Linux";

let
  target = stdenv.hostPlatform.rust.rustcTarget;
  # Keep native root discovery unless the host has no PEM certificates. These
  # are openssl-probe's Linux locations, also used by rustls-native-certs.
  sslCertSetup = ''
    if [ -z "''${SSL_CERT_FILE+x}" ] && [ -z "''${SSL_CERT_DIR+x}" ]; then
      oxide_has_ca=false
      for oxide_cert in \
        /etc/ssl/certs/ca-certificates.crt \
        /etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem \
        /etc/pki/tls/certs/ca-bundle.crt \
        /etc/ssl/ca-bundle.pem \
        /etc/pki/tls/cacert.pem \
        /etc/ssl/cert.pem \
        /opt/etc/ssl/certs/ca-certificates.crt \
        /etc/ssl/certs/* \
        /etc/pki/tls/certs/* \
        /etc/security/certificates/*; do
        if [ -f "$oxide_cert" ] && ${gnugrep}/bin/grep -q '^-----BEGIN CERTIFICATE-----' "$oxide_cert"; then
          oxide_has_ca=true
          break
        fi
      done
      if [ "$oxide_has_ca" = false ]; then
        export SSL_CERT_FILE='${cacert}/etc/ssl/certs/ca-bundle.crt'
      fi
      unset oxide_has_ca oxide_cert
    fi
  '';
  gstPluginsBase = gst_all_1.gst-plugins-base;
  gstPluginsGood = gst_all_1.gst-plugins-good;
  gstPluginsBad = gst_all_1.gst-plugins-bad;
  gstLibav = gst_all_1.gst-libav;
  gstreamer = gst_all_1.gstreamer;
  gstPlugins = [
    gstreamer
    gstPluginsBase
    gstPluginsGood
    gstPluginsBad
    gstLibav
  ];
  runtimeLibs = [
    alsa-lib
    dbus
    fontconfig
    freetype
    gstPluginsBase
    gstPluginsGood
    gstPluginsBad
    gstLibav
    gstreamer
    krb5
    libGL
    libunwind
    libx11
    libxcb
    libxcursor
    libxfixes
    libxinerama
    libxkbcommon
    libxrandr
    openh264
    openssl
    udev
    vulkan-loader
    wayland
  ];
in
rustPlatform.buildRustPackage {
  pname = "oxidelab";
  version = (builtins.fromTOML (builtins.readFile ../Cargo.toml)).workspace.package.version;
  src = ../.;

  cargoLock = {
    lockFile = ../Cargo.lock;
    # rustPlatform.buildRustPackage builds in a network-isolated sandbox.
    # While crates.io dependencies have checksums recorded in Cargo.lock, Git
    # dependencies require fixed-output derivation hashes defined in outputHashes.
    #
    # When updating or adding Git dependencies in Cargo.toml / Cargo.lock:
    # 1. Update Cargo.toml and Cargo.lock first.
    # 2. Run `nix build .#oxidelab -L --show-trace`.
    # 3. If a hash mismatch occurs, check the locked Git revision and update
    #    the matching entry below with the `got:` sha256 output.
    # 4. Run `nix flake check -L` to ensure package checks pass.
    outputHashes = {
      "russh-0.65.0" = "sha256-1PUooricsd02sjf/bQukGDgM/w0+dqj555bpxF6K1dA=";
    };
  };

  nativeBuildInputs = [
    clang
    cmake
    copyDesktopItems
    libclang
    makeWrapper
    nasm
    perl
    pkg-config
  ];

  buildInputs = runtimeLibs;

  cargoBuildFlags = [
    "-p"
    "oxideterm-gpui-app"
    "-p"
    "oxideterm-cli"
    "--bins"
  ];

  cargoTestFlags = [
    "-p"
    "oxideterm-update"
  ];

  strictDeps = true;
  LIBCLANG_PATH = "${libclang.lib}/lib";

  postInstall = ''
    resource_root="$out/bin/resources"
    target_triple="${target}"

    install -d "$resource_root/agents"
    install -d "$resource_root/icons"
    install -d "$resource_root/cli-bin/$target_triple"

    cp -R crates/oxideterm-gpui-app/resources/agents/. "$resource_root/agents/"
    cp -R crates/oxideterm-gpui-app/resources/icons/. "$resource_root/icons/"

    printf 'nix\n' > "$out/bin/PACKAGE_KIND"
    install -Dm644 LICENSE "$out/share/licenses/oxideterm/LICENSE"
    install -Dm644 NOTICE "$out/share/licenses/oxideterm/NOTICE"
    install -Dm644 THIRD_PARTY_NOTICES.md "$out/share/licenses/oxideterm/THIRD_PARTY_NOTICES.md"
    install -Dm644 README.md "$out/share/doc/oxideterm/README.md"

    install -Dm644 crates/oxideterm-gpui-app/resources/icons/32x32.png \
      "$out/share/icons/hicolor/32x32/apps/oxidelab.png"
    install -Dm644 crates/oxideterm-gpui-app/resources/icons/64x64.png \
      "$out/share/icons/hicolor/64x64/apps/oxidelab.png"
    install -Dm644 crates/oxideterm-gpui-app/resources/icons/128x128.png \
      "$out/share/icons/hicolor/128x128/apps/oxidelab.png"
    install -Dm644 crates/oxideterm-gpui-app/resources/icons/128x128@2x.png \
      "$out/share/icons/hicolor/256x256/apps/oxidelab.png"

    wrapProgram "$out/bin/oxidelab" \
      --run ${lib.escapeShellArg sslCertSetup} \
      --prefix LD_LIBRARY_PATH : "${lib.makeLibraryPath runtimeLibs}"

    wrapProgram "$out/bin/oxideterm-native" \
      --set OXIDELAB_CLI_BIN "$out/bin/oxidelab" \
      --run ${lib.escapeShellArg sslCertSetup} \
      --prefix LD_LIBRARY_PATH : "${lib.makeLibraryPath runtimeLibs}" \
      --prefix GST_PLUGIN_SYSTEM_PATH_1_0 : "${lib.makeSearchPathOutput "lib" "lib/gstreamer-1.0" gstPlugins}"

    ln -s "$out/bin/oxidelab" "$resource_root/cli-bin/$target_triple/oxidelab"
  '';

  desktopItems = [
    (makeDesktopItem {
      name = "oxidelab";
      exec = "oxideterm-native %U";
      icon = "oxidelab";
      desktopName = "OxideLab";
      comment = "AI-native workspace for local shells and remote machines";
      categories = [
        "Development"
        "TerminalEmulator"
        "Network"
      ];
      mimeTypes = [
        "x-scheme-handler/ssh"
        "x-scheme-handler/telnet"
        "x-scheme-handler/mosh"
        "x-scheme-handler/rdp"
        "x-scheme-handler/vnc"
      ];
      startupWMClass = "OxideLab";
    })
  ];

  meta = {
    description = "AI-native workspace for local shells and remote machines";
    homepage = "https://github.com/AnalyseDeCircuit/oxideterm";
    license = lib.licenses.gpl3Only;
    mainProgram = "oxideterm-native";
    platforms = lib.platforms.linux;
  };
}

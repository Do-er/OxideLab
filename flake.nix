{
  description = "OxideLab packages for Nix";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
      pkgsFor = system: import nixpkgs { inherit system; };
    in
    {
      legacyPackages = forAllSystems (
        system:
        let
          pkgs = pkgsFor system;
        in
        {
          oxidelab = pkgs.callPackage ./nix/package.nix { };
        }
      );

      packages = forAllSystems (
        system:
        let
          package = self.legacyPackages.${system}.oxidelab;
        in
        {
          default = package;
          oxidelab = package;
        }
      );

      apps = forAllSystems (
        system:
        let
          package = self.packages.${system}.oxidelab;
        in
        {
          default = {
            type = "app";
            program = "${package}/bin/oxideterm-native";
          };
          cli = {
            type = "app";
            program = "${package}/bin/oxidelab";
          };
        }
      );

      devShells = forAllSystems (
        system:
        let
          pkgs = pkgsFor system;
          runtimeLibs = with pkgs; [
            alsa-lib
            dbus
            fontconfig
            freetype
            gst_all_1.gst-plugins-base
            gst_all_1.gst-plugins-good
            gst_all_1.gst-libav
            gst_all_1.gstreamer
            krb5
            libdrm
            libGL
            libunwind
            libx11
            libxcb
            libxcursor
            libxfixes
            libxinerama
            libxkbcommon
            libxrandr
            mesa
            openh264
            openssl
            udev
            vulkan-loader
            wayland
          ];
        in
        {
          default = pkgs.mkShell {
            name = "oxidelab-dev-shell";
            packages =
              with pkgs;
              [
                cargo
                clippy
                clang
                cmake
                git
                just
                makeWrapper
                nasm
                perl
                pkg-config
                rustc
                rustfmt
                libclang
              ]
              ++ runtimeLibs;
            LIBCLANG_PATH = "${pkgs.libclang.lib}/lib";
            # Expose Nix-provided runtime libraries so the cargo-built binary can
            # dlopen Vulkan/EGL/GPU drivers when running via `cargo run`.
            LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath runtimeLibs;
          };
        }
      );

      overlays.default = final: _prev: {
        oxidelab = final.callPackage ./nix/package.nix { };
      };

      nixosModules.oxidelab =
        { lib, pkgs, ... }:
        let
          system = pkgs.stdenv.hostPlatform.system;
          package =
            self.packages.${system}.oxidelab
              or (throw "OxideLab NixOS module does not support system '${system}'");
        in
        {
          imports = [ ./nix/module.nix ];
          programs.oxidelab.package = lib.mkDefault package;
        };
      nixosModules.default = self.nixosModules.oxidelab;

      checks = forAllSystems (system: {
        oxidelab = self.packages.${system}.oxidelab;
      });
    };
}

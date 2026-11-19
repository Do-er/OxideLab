{
  config,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.programs.oxidelab;
in
{
  options.programs.oxidelab = {
    enable = lib.mkEnableOption "OxideLab";
    package = lib.mkPackageOption pkgs "oxidelab" { };
  };

  config = lib.mkIf cfg.enable {
    environment.systemPackages = [ cfg.package ];
  };
}

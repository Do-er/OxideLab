<!-- RELEASE_CHANGELOG -->

<!-- RELEASE_DOWNLOADS -->

<details>
<summary>📌 Installation Tips / 安装提示</summary>

### macOS

Downloaded `.dmg` files may be quarantined by Gatekeeper. Run in Terminal:

```bash
xattr -cr ~/Downloads/OxideLab_*.dmg
# or after install / 或安装后
xattr -cr /Applications/OxideLab.app
```

### Windows

If SmartScreen warns, click **More info** -> **Run anyway**.

若 SmartScreen 弹出警告，点击 **更多信息** -> **仍要运行**。

### Linux

```bash
# AppImage
chmod +x OxideLab_*_linux_*.AppImage && ./OxideLab_*_linux_*.AppImage

# Debian/Ubuntu
sudo dpkg -i OxideLab_*_linux_*.deb && sudo apt-get install -f

# Fedora/RHEL-compatible systems
sudo dnf install ./OxideLab_*_linux_*.rpm
```

</details>

## 🔗 Links

- GitHub: https://github.com/Do-er/OxideLab
- Changelog: https://github.com/Do-er/OxideLab/blob/dev/.github/release-notes/stable-changelog.md

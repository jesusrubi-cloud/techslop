#!/usr/bin/env bash
# Non-root Debian 13 installation. APT verifies signed repository metadata/checksums.
set -euo pipefail
. /etc/os-release
if [[ "$ID" != debian || "$VERSION_ID" != 13 ]]; then
  echo 'This non-root installer supports Debian 13. On other systems install espeak-ng with your trusted system package manager.' >&2
  exit 1
fi
voice_root="${1:-/workspace/.tools/espeak}"
voice_root="$(realpath -m "$voice_root")"
if [[ -f "$voice_root/root/usr/lib/x86_64-linux-gnu/libespeak-ng.so.1" ]]; then
  echo "eSpeak already installed at $voice_root/root"
  exit 0
fi
if [[ "$(dpkg --print-architecture)" != amd64 ]]; then
  echo 'This non-root layout currently supports amd64.' >&2
  exit 1
fi
apt_root="$voice_root/apt-state"
mkdir -p "$apt_root/lists/partial" "$apt_root/cache/archives/partial" "$apt_root/empty" "$voice_root/packages"
cat > "$apt_root/config" <<EOF
Dir::Etc::parts "$apt_root/empty";
Dir::Etc::main "$apt_root/empty-config";
Dir::Etc::sourcelist "$apt_root/sources.list";
Dir::Etc::sourceparts "$apt_root/empty";
Dir::State::lists "$apt_root/lists";
Dir::Cache "$apt_root/cache";
Debug::NoLocking "true";
EOF
cat > "$apt_root/sources.list" <<'EOF'
deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian trixie main
EOF
APT_CONFIG="$apt_root/config" apt-get update
cd "$voice_root/packages"
APT_CONFIG="$apt_root/config" apt-get download espeak-ng espeak-ng-data libespeak-ng1 libpcaudio0 libsonic0
for package in *.deb; do dpkg-deb -x "$package" "$voice_root/root"; done
printf 'Installed eSpeak NG under %s/root\n' "$voice_root"

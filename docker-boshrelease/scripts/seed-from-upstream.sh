#!/usr/bin/env bash
# Seed the local blobstore and blobs/ from a published docker release tarball so
# `bosh create-release --final` can reuse unchanged packages and jobs.
# Usage: scripts/seed-from-upstream.sh path/to/docker-<version>.tgz
# Requires: bosh CLI, tar, shasum.
set -euo pipefail

REL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARBALL="${1:?usage: $0 path/to/docker-<version>.tgz}"
[[ -f "${TARBALL}" ]] || { echo "not a file: ${TARBALL}" >&2; exit 1; }

BLOBSTORE="$(bosh int "${REL_DIR}/config/final.yml" --path /blobstore/options/blobstore_path)"
[[ "${BLOBSTORE}" = /* ]] || BLOBSTORE="${REL_DIR}/${BLOBSTORE}"
mkdir -p "${BLOBSTORE}" "${REL_DIR}/blobs"

TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT
tar -xzf "${TARBALL}" -C "${TMP}"
MF="${TMP}/release.MF"
echo "seeding from $(bosh int "${MF}" --path /name) $(bosh int "${MF}" --path /version) into ${BLOBSTORE}"

verify() { # expected-digest file   (digest is "sha256:<hex>" or bare sha1 hex)
  local expected="$1" file="$2"
  if [[ "${expected}" == sha256:* ]]; then
    echo "${expected#sha256:}  ${file}" | shasum -a 256 -c - >/dev/null
  else
    echo "${expected}  ${file}" | shasum -a 1 -c - >/dev/null
  fi
}

seed() { # kind name src
  local kind="$1" name="$2" src="$3" fp sha id
  local index="${REL_DIR}/.final_builds/${kind}/${name}/index.yml"
  [[ "${kind}" == license ]] && index="${REL_DIR}/.final_builds/license/index.yml"
  if [[ ! -f "${index}" ]]; then
    echo "skip ${kind}/${name}: no final-build index here (not part of this fork)"
    return
  fi
  if [[ "${kind}" == license ]]; then
    fp="$(bosh int "${MF}" --path /license/fingerprint)"
    sha="$(bosh int "${MF}" --path /license/sha1)"
  else
    fp="$(bosh int "${MF}" --path "/${kind}/name=${name}/fingerprint")"
    sha="$(bosh int "${MF}" --path "/${kind}/name=${name}/sha1")"
  fi
  id="$(bosh int "${index}" --path "/builds/${fp}/blobstore_id")"
  verify "${sha}" "${src}"
  cp "${src}" "${BLOBSTORE}/${id}"
  echo "seeded ${kind}/${name} fingerprint=${fp:0:12} -> ${id}"
}

# `bosh int` re-serializes with sorted keys, so "name:" may or may not be the
# first key of each list entry; match both "- name: x" and "  name: x".
for kind in packages jobs; do
  for name in $(bosh int "${MF}" --path "/${kind}" | awk '$1=="name:"{print $2} $2=="name:"{print $3}'); do
    seed "${kind}" "${name}" "${TMP}/${kind}/${name}.tgz"
  done
done
seed license license "${TMP}/license.tgz"

# Restore blobs/ from the package tarballs; also store each blob under its object_id.
for blob in $(bosh int "${REL_DIR}/config/blobs.yml" | awk -F: '/^[^ ]/{print $1}'); do
  found=""
  for pkg in "${TMP}"/packages/*.tgz; do
    if tar -tzf "${pkg}" | grep -qx "./${blob}"; then
      tar -xzf "${pkg}" -C "${REL_DIR}/blobs" "./${blob}"
      sha="$(awk -v k="${blob}:" '$1==k{f=1} f&&/^  sha:/{print $2; exit}' "${REL_DIR}/config/blobs.yml")"
      oid="$(awk -v k="${blob}:" '$1==k{f=1} f&&/^  object_id:/{print $2; exit}' "${REL_DIR}/config/blobs.yml")"
      verify "${sha}" "${REL_DIR}/blobs/${blob}"
      cp "${REL_DIR}/blobs/${blob}" "${BLOBSTORE}/${oid}"
      echo "restored blob ${blob} from $(basename "${pkg}") (object_id ${oid})"
      found=1
      break
    fi
  done
  [[ -n "${found}" ]] || { echo "blob ${blob} not found in any package tarball" >&2; exit 1; }
done

echo "done. check with: (cd ${REL_DIR} && bosh blobs)"

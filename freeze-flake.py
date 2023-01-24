#!/usr/bin/env python3

import json
import pathlib
import pprint
import string
import subprocess

FLAKE_NIX = string.Template("""{
  inputs = {
    original = {
      url = "${original_url}";
      inputs = {
        ${inputs}
      };
    };
  };

  outputs = { original }:
  {
  };
}""")

def get_flakeref(locked):
    flakeref = f"{locked['type']}:{locked['owner']}/{locked['repo']}/{locked['rev']}?narHash={locked['narHash']}"
    if 'host' in locked:
        flakeref += f"&host={locked['host']}"
    return flakeref


def get_flake_json(flakeref):
    json_str = subprocess.check_output(["nix", "flake", "metadata", flakeref, "--json", "--no-write-lock-file"])
    return json.loads(json_str)


def get_flake_store_path(flakeref):
    json_str = subprocess.check_output(["nix", "flake", "prefetch", flakeref, "--json"])
    return json.loads(json_str)["storePath"]


def freeze_flake(flakeref, output_path):
    flakes = {}
    original = get_flake_json("clearpath")
    for name, data in original["locks"]["nodes"].items():
        if name != "root":
            ref = get_flakeref(data["locked"])
            flakes[name] = {
                "ref": ref,
                "path": get_flake_store_path(ref),
                "inputs": data.get("inputs")
            }
    # pprint.pprint(flakes)

    input_lines = []
    for name, data in flakes.items():
        input_lines.append(f'{name}.url = "path:{data["path"]}";')
        for input_name, input_data in (data["inputs"] or {}).items():
            if isinstance(input_data, str):
                input_lines.append(f'{name}.inputs.{input_name}.url = "path:{flakes[input_data]["path"]}";')


    flake_nix_text = FLAKE_NIX.substitute({
      "original_url": f'path:{original["path"]}',
      "inputs": "\n        ".join(input_lines)
    })
    output_path.mkdir(exist_ok=True)
    output_flake_nix = output_path / "flake.nix"
    output_flake_nix.write_text(flake_nix_text)
    print(flake_nix_text)
    


if __name__ == "__main__":
    freeze_flake("clearpath", pathlib.Path("/tmp/flake"))

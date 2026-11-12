# Preview update channel

This definition contains the reviewed `0.8.0-source-rc2` package with the `pluginURL` attribute required by Unraid's update checker. Its payload and transaction scripts are byte-for-byte identical to the source-built candidate. The only change is the update URL in the opening PLUGIN tag.

- Source package SHA-256: `1bfa566f2d378fe25831b87dae5c4753ba095c65cdfe058d007d5cbce935d273`
- Preview definition SHA-256: `8ea43994ce7626a86db9132de09381d4b717a47ad5d9064160bd1154b0804062`

Prepare or verify it from the repository root:

```sh
python3 tools/prepare_update_manifest.py \
  plugin/candidates/source-rc2/rp2040-fan-control-webui-integration-serial-v2-auditfix19.plg \
  plugin/channels/preview \
  --expected-sha256 1bfa566f2d378fe25831b87dae5c4753ba095c65cdfe058d007d5cbce935d273
```

Add `--verify` to check the stored definition, sidecar and provenance record without writing files. The tool does not install or execute the plugin.

The definition URL stays on the `source-tree-review` branch. Keep the branch available until installed preview definitions have migrated. Publish later reviewed preview versions by deliberately replacing this definition and regenerating its sidecar/provenance. The checker compares the version in the remote definition; equal versions should show as current. A newer preview must preserve source verification and pass CI before updating this pointer.

Do not point an installed stable channel here. Installing updates requires a stopped and explicitly disabled daemon; checking updates does not change daemon state. Current Unraid installations may adopt this metadata-only variant only after verifying that removal of its one added attribute restores their exact installed reviewed PLG bytes. Back up the original definition first. This preserves runtime code and avoids restarting hardware control merely to enable checking.

# Blockless Artifact Store Binding

`file_operation` is the only way browser skills read or write project files, logs, generated code, manifests, and rendered artifacts.

Paths are POSIX-style project-relative paths. Blockless owns persistence through its project store, currently backed by browser storage such as IndexedDB, OPFS, downloaded archive snapshots, or an equivalent project store.

Required operations:

| Operation | Purpose |
| --- | --- |
| `read` | Read a project-relative file. |
| `write` | Create or replace a project-relative file. |
| `list` | Enumerate files under a project-relative path. |
| `delete` | Remove a project-relative file or directory. |
| `snapshot` | Export a named project snapshot for review or restore. |

The binding must preserve structured artifacts such as phase envelopes, validation reports, serial logs, diagrams, firmware metadata, and deployment manifests.

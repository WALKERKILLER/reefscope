# Vendored inference code

`coral_model.py` is the loader and inference code delivered with the coral checkpoint package `coral-final-weights-v2` (exported 2026-11-02 by the project's coral team). It is kept byte-identical to the delivered file, SHA-256 `b93ce7ac9a08be395f6c02d4632523279dc27d8148a8639aa54138a0e6572d55`, because its numeric path was verified against the checkpoint; `app/analysis/coral.py` adapts it without editing it. A new delivery replaces the file and registers a new model ID.

The checkpoint builds on [EPFL-ECEO/segformer-b5-finetuned-coralscapesv2-1024-1024-95_class](https://huggingface.co/EPFL-ECEO/segformer-b5-finetuned-coralscapesv2-1024-1024-95_class) at revision `a81205e666767b8602c6e7ad8da69b1e013bafdd`, licensed Apache-2.0. The weights are not part of this repository. Transformers and safetensors remain external dependencies under their own licenses.

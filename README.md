## localGP collection design

localGP grids come in a few similar flavors: integrals over pressure ranges; interpolations to specific pressure levels; and unleveled grids, like mixed layer depth or sea height. 
All of these can be represented as Argovis-schema grids, with the generalization that integral grids need ranges allowed in the 'levels' property of their metadata.

### integral grids

 - plan (Dec 2025) is to combine all the future integral grids onto a single collection `localGPintegral`, with metadata on `localGPMeta`.
   - advantage: minimal document number -> minimal index size
   - problems: assumes every variable that gets added has a similar level spectrum, otherwise we're going to end up with a lot of null padding.
 - create collection schema with the usual grid scripts from db-schema repo.
 - see `populate_db.py` for run instructions
   - built to consume localGP full field matlab outputs describing a single variable on [20.5,379.5] and [-89.5,89.5].

### interp grids and unleveled grids

 - TBD. probably just regular grids, questions remain ATOW what level spectra will be used, how consistent this will be.

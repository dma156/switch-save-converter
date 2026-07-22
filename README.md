# Switch Save Converter

- This program was written with assistance from Proton's Lumo AI. 

Converts save file formats between Eden, Checkpoint and JKSV.

There are two modes, **Manual mode** is a simple 'point the source to a Checkpoint folder or JKSV/Eden zip file and convert'.

**Newest Save File mode** looks for the most recently modified Checkpoint folder or JKSV file inside a parent folder and converts that to the desired target format.

## Save file structure

### Checkpoint

#### Checkpoint save format
A folder which includes the actual game save file(s) in the format of `Date Switch User` (YYYYMMDD-HHmmss username) e.g. `20260223-162127 Guntar`

#### Checkpoint Folder structure
- A folder with the name format of the Switch game ID in Hex (0x0...) and then the name of the game, or the same ID repeated.
- This folder will then include the actual Checkpoint save(s) which are folder(s) containing the actual game save data

```
\-- Checkpoint
	\-- saves
		\-- 0x0012345B769 Best Game in the World
			\-- 20260223-162127 Guntar
				├── main
				├── trade
				├── secretes!
		\-- 0x00123D56789 0x00123456789
			\-- 20260223-162129 Guntar
				├── save.bin
```

### JKSV

#### JKSV save format 
A zip file with naming convention of `Switch User - Date` in format `User - YYYY-MM-DD_HH-mm-ss.zip` e.g. `EVIL ME - 2026-04-12_18-46-11.zip`. Files are directly inside, with no folders.

#### JKSV Folder structure
- JKSV folder will contain folders with names of the Switch Title
- Inside each folder will be the save files in zip format. Save data files are directly inside, with no folders (unlike in Eden).
```
\-- JKSV
	\-- The Adventure of Bolt Having a Good Time
		*── EVIL ME - 2026-04-12_18-46-11.zip
			\-- folder
				├── file1
			├── file2
			├── file4U
			├── save
		*── -silly-name0- - 2026-04-12_18-47-11.zip
			├── save
```

### Eden
Eden exports saves in zip format with a folder inside. Therefore no folder structure will be checked. This singular zip file has the naming format of `Game Name Save Data - Date.zip` e.g. `PocketPals Purpl save data - 2026-05-20 18_02.zip` or `Tomisdashing Life_ Living the Nightmare save data - 2026-05-28 17_36.zip`.

Inside will be a folder named after the Switch Title ID (so without the 0x0 hex prefix) e.g. `01008F6D12349`, then inside that folder will be the actual save files.
```
*── PocketPals Purpl save data - 2026-05-20 18_02.zip
	\-- folder
		├── file1
	├── file2
	├── file4U
	├── save
```

### Acknowledgements

- [Forked Switch Games JSON Repo](https://github.com/Producdevity/switch-games-json)

- [Original Switch Games JSON Repo](https://github.com/fmartingr/switch-games-json)

- [SwitchBrew](https://switchbrew.org/w/index.php?title=Title_list/Games)



# Switch Save Converter

- This program was written mostly with Proton's Lumo AI. 

Converts save file formats between Eden, Checkpoint and JKSV



### Save file structure

- Checkpoint

Checkpoint save format 
A folder which includes the actual game save file(s) in the format of [Date Switch User] (YYYYMMDD-HHmmss User) e.g. 20260223-162127 guntar

Checkpoint Folder structure 
> A folder with the name format of the Switch game ID in Hex (OxO...) and then the name of the game, or the same ID repeated. The repeated ID format is common for Pokemon games.
	> This folder will then include the actual Checkpoint save folder(s) containing the game save file(s) in the format of [Date Switch User] (YYYYMMDD-HHmmss User) e.g. 20260223-162127 guntar
		> Actual game files

- JKSV

JKSV save format 
A zip file named: Switch User - Date in format User - YYYY-MM-DD_HH-mm-ss.zip e.g. EVIL ME - 2026-04-12_18-46-11.zip. Files are directly inside, with no folders.

JKSV Folder structure
> Switch Title (e.g. Pokemon Violet)
	> Zip file named: Switch User - Date in format User - YYYY-MM-DD_HH-mm-ss.zip e.g. EVIL ME - 2026-04-12_18-46-11.zip
		> Files directly inside, with no folders.

- Eden
No folder structure will be checked, just a singular zip file that has the format of [Game Name Save Data - Date.zip] e.g. Pokémon Violet save data - 2026-05-20 18_02.zip
	> Inside will be a folder named after the 0x0 Switch Hex ID
		> Then inside the folder will be the actual save files
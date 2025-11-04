I made a tool with the help of Ai to add the run lines (ORFIX / NNFIx) to more Complex toggle mods with a single ini and normal merged.inis

Please only run it in the folder of the broken mod not the generall mod folder because it will break all mods. 

How to use it:

Place it into the folder of the mod you want fixed and run it
It will ask you if you want the extra parts renamed ps-t0 =... to ps_t1 =... but it should only be needed for Skirk
Then it will ask if it should also search in sub folders if you use it on a normal merged mod press y or n depending on your usecase
It will now show/ask you if you want to exclude parts from changing press n if you don't want to exclude then and change them or y if the part isn't green or weird 
Do this for every part asked and you will get to Proceed with these changes? (y/n): press y to start or n to abort it. 

If the mod is still broken simply run it again and try a different exclusion or before running it again delete the ini and rename the backup to Name.ini or merged.ini
The backups have date and time stamps to make it easier to keep track of. 

A few tips:
For skirk mods atleast from LewdLad you need to exclude the LimbsBody Section with y otherwise they will turn red 
This tool could have problems if the facefix tool is ran before but it also might work it is still a bit janky sorry for that
Also if you use Gimi get the latest ORFix and ORFixApi  https://github.com/leotorrez/LeoTools/tree/main/releases

If you find any bugs please comment and if possible like the mod with which you had a bug. 
Also if you can improove it in any way feel free to edit it or make suggestions in the comments or on github 
Link to the latest release on github: https://github.com/Sanddino00/ORFIX_for_Complex_Mods/releases
/*
	STARFLIGHT - THE LOST COLONY
	main.cpp - main function that launches the game class
	Author: Coder
	Date:
*/

#include "env.h"
#include <allegro.h>
#ifdef A4SDL
#include <SDL3/SDL_main.h>   //SDL supplies WinMain on Windows and calls main()
#endif
#include "Game.h"
#include "LogFile.h"


//global engine object
Game *g_game;

int main(int argc, char **argv)
{
#ifdef A4SDL
	//find data/ (next to the executable, in an app bundle, or the dev tree)
	//before anything opens a file
	a4_init_paths();
#endif
	g_game = new Game();
	g_game->Run();
	g_game = NULL;

   return 0;
}
END_OF_MAIN()

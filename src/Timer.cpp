#include <allegro.h>
#include "Timer.h"
#include <chrono>


Timer::Timer(void)
{
	reset();
}

Timer::~Timer(void){}

//milliseconds since the program started (portable: steady_clock replaces
//clock() on Windows and gettimeofday() elsewhere)
long Timer::getTimer()
{
	static const std::chrono::steady_clock::time_point origin = std::chrono::steady_clock::now();
	return (long)std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - origin).count();
}

void Timer::setTimer(long value)
{
	timer_start = value;
}


long Timer::getStartTimeMillis()
{
	return getTimer() - timer_start;
}

//warning: this is a blocking sleep
void Timer::sleep(long ms)
{
	long start = getTimer();
	while (start + ms > getTimer());
}

void Timer::reset()
{
	timer_start = getTimer();
	stopwatch_start = timer_start;
}

bool Timer::stopwatch(long ms)
{
	if ( getTimer() > stopwatch_start + ms ) {
		stopwatch_start = getTimer();
		return true;
	}
	else return false;
}


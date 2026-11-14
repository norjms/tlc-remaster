
#ifndef _TIMER_H
#define _TIMER_H 1

#include "env.h"

class Timer
{
private:
	long timer_start;
	long stopwatch_start;

public:
	Timer(void);
	~Timer(void);
	long getTimer();
	void setTimer(long value);

	long getStartTimeMillis();

	void sleep(long ms);
	void reset();
	bool stopwatch(long ms);
};

#endif

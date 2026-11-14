#pragma once

/*
 * AudioSystem: thin wrapper over miniaudio (formerly FMOD Ex).
 *
 * The public interface is unchanged from the FMOD version so that no
 * call sites had to change. miniaudio types are only forward declared
 * here; miniaudio.h is included by AudioSystem.cpp alone.
 */

#include <iostream>
#include <string>
#include <vector>
#include <set>
#include "Game.h"

struct ma_engine;
struct ma_sound;
class AudioSystem;

class Sample
{
	friend class AudioSystem;

private:
	std::string name;
	std::string filename;
	bool loop;
	bool paused;
	bool streamed;          //music is streamed from disk, sound effects are decoded up front
	float volume;
	AudioSystem *owner;     //NULL once the owning AudioSystem has shut down
	ma_sound *sound;        //primary voice
	std::vector<ma_sound*> extraVoices;   //overlapping one-shot plays of the same effect

	void ReleaseVoices();

public:
	Sample(void);
	~Sample(void);
	std::string getName() { return name; }
	void setName(std::string value) { name = value; }

	void SetVolume(float volume);
	void SetLoop(bool doLoop);
	bool GetLoop(void){ return loop; }
	void SetPaused(bool doPause);
	bool GetPaused(void){ return paused; }
};

class AudioSystem
{
	friend class Sample;

private:
	ma_engine *engine;      //NULL when audio is disabled or unavailable
	typedef std::vector<Sample*> Samples;
	typedef std::vector<Sample*>::iterator SampleIterator;
	Samples samples;        //named samples, owned by AudioSystem
	std::set<Sample*> live; //every Sample created, named or not
	bool bPlay;

	Sample *CreateSample(const std::string &filename, float volume, bool stream);
	ma_sound *CreateVoice(Sample *sample);
	void Forget(Sample *sample);

public:
	AudioSystem(void);
	~AudioSystem(void);

	bool Init();
	void Update(); //must be called once per frame

	bool Load(std::string filename, std::string name, float volume = 1.0f);
	Sample* Load(std::string filename, float volume = 1.0f);
	bool LoadMusic(std::string filename, std::string name, float volume = 0.4f);
	Sample* LoadMusic(std::string filename, float volume = 0.4f);
	bool Play(std::string name, bool doLoop=false);
	bool Play(Sample *sample, bool doLoop=false);
	bool PlayMusic(std::string name, bool doLoop=true);
	bool PlayMusic(Sample *sample, bool doLoop=true);

	void PauseMusic(std::string name);
	void UnpauseMusic(std::string name);
	void Stop(std::string name);
	void Stop(Sample *sample);
	void StopAll();
	void StopAllExcept(std::string name);
	void Delete(std::string name);
	bool IsPlaying(std::string name);
	bool IsPlaying(Sample *sample);
	bool SampleExists(std::string name);
	Sample *FindSample(std::string name);

};

#include <iostream>
#include <fstream>
using namespace std;
#include "LogFile.h"

//Opened on first use rather than during static initialization, so it
//lands in the game's working directory (set up at the start of main) and
//never runs before or after the streams library. Every translation unit
//has its own 'debug' LogFile, so none of them closes the shared stream;
//it closes itself at exit.
static std::ofstream& logstream()
{
    static std::ofstream f("output.txt");
    return f;
}
#define out logstream()

LogFile::LogFile() {}
LogFile::~LogFile() {}
void LogFile::Print(string s)
{
    out << s << endl;
}
void LogFile::Print(char c[])
{
    out << c << endl;
}
std::ofstream& LogFile::operator<<(const char *s)
{
    out << s;
    return out;
}
std::ofstream& LogFile::operator<<(char c[])
{
    out << c;
    return out;
}
std::ofstream& LogFile::operator<<(string s)
{
    out << s;
    return out;
}
std::ofstream& LogFile::operator<<(double d)
{
    out << d;
    return out;
}
std::ofstream& LogFile::operator<<(float f)
{
    out << f;
    return out;
}
std::ofstream& LogFile::operator<<(int i)
{
    out << i; 
    return out;
}
std::ofstream& LogFile::operator<<(bool b)
{
    if (b) out << "True";
    else out << "False";
    return out;
}

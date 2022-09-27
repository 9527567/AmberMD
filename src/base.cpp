//
// Created by jack on 2022/9/19.
//
#include "base.hpp"

#include "fmt/core.h"
#include "fmt/os.h"
#include <utility>
Base::Base(std::string name, SystemInfo systemInfo, std::string restranintmask, float restraint_wt, float cut) : name_(std::move(name)), systemInfo_(systemInfo), cut_(cut), restraintMask_(restranintmask), restraint_wt_(restraint_wt)
{
}
void Base::operator()(float cut)
{
}
void Base::writeInput()
{
    fmt::ostream out = fmt::output_file(name_ + ".in");
    out.print("Minimization: " + name_ + "\n");
    out.print("&cntrl\n");
}
void Base::Run()
{
    writeInput();
    charmmWater();
    restraint();
    writeEnd();
}
void Base::charmmWater()
{
    if (systemInfo_.getHasCharmmWater())
    {
        hasCharmmWater_ = true;
    }
    if (hasCharmmWater_)
    {
        fmt::ostream out = fmt::output_file(name_ + ".in", fmt::file::WRONLY | fmt::file::APPEND);
        out.print("   WATNAM = 'TIP3', OWTNM = 'OH2',");
    }
}
void Base::writeEnd()
{
    fmt::ostream out = fmt::output_file(name_ + ".in", fmt::file::WRONLY | fmt::file::APPEND);
    out.print("&end\n");
}
void Base::restraint()
{
    setRestraintMask(restraintMask_);
    fmt::ostream out = fmt::output_file(name_ + ".in", fmt::file::WRONLY | fmt::file::APPEND);
    if (restraintMask_.empty())
    {
        out.print("ntr=0");
        out.print("\n");
    } else
    {
        out.print("ntr=1,");
        out.print("restraintmask={},", restraintMask_);
        out.print("restraint_wt={},", restraint_wt_);
        out.print("\n");
    }
}
// 最简单的版本
void Base::setRestraintMask(std::string appendMask)
{
    if (restraintMask_.empty())
    {
        restraintMask_ = fmt::format("\":1-{}!@H=\"", systemInfo_.getNprotein() + systemInfo_.getnDna() + systemInfo_.getnRna() + systemInfo_.getnLipid() + systemInfo_.getnCarbo());

    } else
    {
        restraintMask_ = fmt::format("\":1-{}&!@H=|:{}\"", systemInfo_.getNprotein() + systemInfo_.getnDna() + systemInfo_.getnRna() + systemInfo_.getnLipid() + systemInfo_.getnCarbo(), appendMask);
    }
}
Base *Base::setCut(float cut)
{
    cut_ = cut;
    return this;
}
void Base::appendMask(std::string mask)
{
}
Base *Base::setNTwx(int ntwx)
{
    nTwx_ = ntwx;
    return this;
}
Base *Base::setNTwr(int ntwr)
{
    nTwr_ = ntwr;
    return this;
}
Base *Base::setNTpr(int ntpr)
{
    nTpr_ = ntpr;
    return this;
}
//
// Created by jack on 2022/9/19.
//
#include "common.hpp"
#include "fmt/format.h"

#include "pybind11/pybind11.h"
#include <atomic>
#include <cstring>
#include <filesystem>
#include <optional>
#include <signal.h>
#include <sys/wait.h>
#include <vector>
namespace py = pybind11;
std::vector<std::string> executeCMD(const std::string &strCmd)
{

    signal(SIGINT, signalHandler);
    char buf[1024] = {0};
    FILE *pf = nullptr;
    if ((pf = popen(strCmd.c_str(), "r")) == nullptr)
    {
        throw std::runtime_error(fmt::format("{} run failed!\n", strCmd));
    }

    std::string strResult;
    while (fgets(buf, sizeof buf, pf))
    {
        strResult += buf;
    }
    if (pclose(pf) != 0)
    {
        throw std::runtime_error(fmt::format("{} run failed!\n", strCmd));
    }
    std::vector<std::string> result;
    std::string temp;
    for (auto i: strResult)
    {
        temp.push_back(i);
        if (i == '\n')
        {
            result.emplace_back(temp);
            temp.clear();
        }
    }

    return result;
}

[[maybe_unused]] std::string executeCMD2(const std::vector<std::string> &args,
                                         const bool inc_stderr)
{
    int stdout_fds[2];
    pipe(stdout_fds);

    int stderr_fds[2];
    if (!inc_stderr)
    {
        pipe(stderr_fds);
    }

    const pid_t pid = fork();
    if (!pid)
    {
        close(stdout_fds[0]);
        dup2(stdout_fds[1], 1);
        if (inc_stderr)
        {
            dup2(stdout_fds[1], 2);
        }

        close(stdout_fds[1]);

        if (!inc_stderr)
        {
            close(stderr_fds[0]);
            dup2(stderr_fds[1], 2);
            close(stderr_fds[1]);
        }

        std::vector<char *> vc(args.size() + 1, nullptr);
        for (size_t i = 0; i < args.size(); ++i)
        {
            vc[i] = const_cast<char *>(args[i].c_str());
        }

        execvp(vc[0], &vc[0]);
        exit(0);
    }

    close(stdout_fds[1]);

    std::string out;
    const int buf_size = 4096;
    char buffer[buf_size];
    do {
        const ssize_t r = read(stdout_fds[0], buffer, buf_size);
        if (r <= 0)
        {
            break;
        }

        if (true)
        {
            out.append(buffer, r);
        }
    } while (errno == EAGAIN || errno == EINTR);

    close(stdout_fds[0]);

    if (!inc_stderr)
    {
        close(stderr_fds[1]);
        do {
            const ssize_t r = read(stderr_fds[0], buffer, buf_size);
            if (r <= 0)
            {
                break;
            }
        } while (errno == EAGAIN || errno == EINTR);

        close(stderr_fds[0]);
    }

    int r, status;
    do {
        r = waitpid(pid, &status, 0);
    } while (r == -1 && errno == EINTR);

    return out;
}
void signalHandler(int signum)
{
    fmt::print("Interrupt signal{} received.\n", signum);
    exit(signum);
}
void raiseHandler(int signum)
{
    raise(signum);
}
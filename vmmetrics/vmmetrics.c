#include <stdio.h>
#include <errno.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/syscall.h>

int main(int argc, char **argv)
{
  int error;
  unsigned int level = 0;

  // syscall is deprecated but I don't know how else to call this.
  error = syscall(SYS_memorystatus_get_level, &level);
  if (error)
  {
    perror("memorystatus_get_level failed:");
    exit(-1);
  }

  printf("Free memory percent: %u\n", level);
  return error;
}

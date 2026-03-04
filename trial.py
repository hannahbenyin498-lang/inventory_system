#!/bin/python3

import math
import os
import random
import re
import sys

#
# Complete the 'getRemovableIndices' function below.
#
# The function is expected to return an INTEGER_ARRAY.
# The function accepts following parameters:
#  1. STRING str1
#  2. STRING str2
#

def getRemovableIndices(str1, str2):
    n1, n2 = len(str1), len(str2)
    
    # Basic check: str1 must be exactly one character longer
    if n1 != n2 + 1:
        return [-1]
    
    # 1. Find how many characters match from the beginning (Prefix)
    prefix_match = 0
    while prefix_match < n2 and str1[prefix_match] == str2[prefix_match]:
        prefix_match += 1
        
    # 2. Find how many characters match from the end (Suffix)
    suffix_match = 0
    while suffix_match < n2 and str1[n1 - 1 - suffix_match] == str2[n2 - 1 - suffix_match]:
        suffix_match += 1
        
    # 3. Determine the valid range of indices
    # The 'start' of our range is the first index from the right where strings differ
    # The 'end' of our range is the first index from the left where strings differ
    low = n1 - 1 - suffix_match
    high = prefix_match
    
    # If the prefix and suffix don't overlap enough to bridge the 1-char gap
    if low > high:
        return [-1]
        
    # Return the range of indices in increasing order
    return list(range(low, high + 1))

if __name__ == '__main__':
    str1 = input()

    str2 = input()

    result = getRemovableIndices(str1, str2)

    print('\n'.join(map(str, result)))
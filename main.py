def fizzbuzz(n):
    """
    Calculate FizzBuzz up to the given input n.
    
    Args:
        n (int): The upper limit for FizzBuzz calculation
        
    Returns:
        list: A list containing FizzBuzz results from 1 to n
    """
    result = []
    for i in range(1, n + 1):
        if i % 3 == 0 and i % 5 == 0:
            result.append("FizzBuzz")
        elif i % 3 == 0:
            result.append("Fizz")
        elif i % 5 == 0:
            result.append("Buzz")
        else:
            result.append(i)
    return result


def main():
    print("Hello from au!")
    
    # Test the FizzBuzz function
    print("\nFizzBuzz up to 15:")
    fizz_result = fizzbuzz(15)
    for i, value in enumerate(fizz_result, 1):
        print(f"{i}: {value}")


if __name__ == "__main__":
    main()
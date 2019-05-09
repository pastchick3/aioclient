# AIOClient

- [AIOClient](#aioclient)
  - [Overview](#overview)
  - [Client](#client)
    - [Build Request](#build-request)
    - [Initialize Client](#initialize-client)
    - [Send Request and Get Response](#send-request-and-get-response)
    - [Process Response](#process-response)
  - [Interpreter](#interpreter)
    - [Inspiration](#inspiration)
    - [Introduction](#introduction)
    - [Some Details About `<request_expr>`](#some-details-about-requestexpr)
    - [Some Details About `<result_expr>`](#some-details-about-resultexpr)
    - [Implicit `<then_expr>`](#implicit-thenexpr)
    - [Full Grammar Specification](#full-grammar-specification)
  - [Logging, Testing, and Dependencies](#logging-testing-and-dependencies)


----------------------------------------------------------------------------------------------------


## Overview

AIOClinet is a general-purpose asynchronous HTTP Client library. AIOClient builds on AIOHTTP with a threaded version so it can work with non-async programs. In addition, there is a experimental interpreter using a really simple DSL.

AIOClient aims to provide single-thread-mindset Python programmers with the power of concurrency, while avoiding all headaches associated with multi-threading and coroutines.

- Simple Request
    
        import asyncio
        from aioclient import Client, Request

        async def main():
            async with Client() as client:
                request = Request('https://www.baidu.com/')
                response = await client.submit(request)
                return response.url
        
        url = asyncio.run(main())

- Multiple Request

        import asyncio
        from aioclient import Client, Request

        async def main():
            async with Client() as client:
                requests = [
                    Request('https://www.baidu.com/'),
                    Request('https://www.douban.com/'),
                ]
                responses = await client.submit(requests)
                return [resp.url for resp in responses]
        
        urls = asyncio.run(main())

- Thread Client

        from aioclient import Request, ThreadClient

        with ThreadClient() as client:
            request = Request('https://www.baidu.com/')
            response = client.submit(request).result()
            url = response.url

- Use Interpreter

        import asyncio
        from aioclient import Client, Interpreter

        async def main():
            script = '''
                let request = get from 'https://www.baidu.com/'
                let future = send request
                let response = wait future
                process response as html with {{
                    return obj.xpath('//title')[0].text
                }}
            '''
            async with Interpreter() as interpreter:
                return await interpreter.run(script)
        
        title = asyncio.run(main())

- Use Implicit Expression

        import asyncio
        from aioclient import Client, Interpreter

        async def main():
            script = '''
                get from 'https://www.baidu.com/'
                then send
                then wait
                then process
                    whose status equals 200 as html with {{
                        return obj.xpath('//title')[0].text
                    }}
                    otherwise as bytes with {{
                        return response.status, response.reason
                    }}
            '''
            async with Interpreter() as interpreter:
                return await interpreter.run(script)
        
        title = asyncio.run(main())


----------------------------------------------------------------------------------------------------


## Client

### Build Request

First or all, we need to build `Request`, which can be imported from `aioclient`. If you want to construct POST requests, also import `HTTPMethod`. (All public classes are directly available in `aioclient` namespace. From now on, we will skip all `import`.)

    from aioclient import HTTPMethod, Request

    request = Request(
        url='https://www.baidu.com/',
        method=HTTPMethod.POST,
    )

`Request` takes a few arguments, which are listed as follow. Notice except `url`, all others are keyword-only arguments:

- `url: Union[str, URL]`  
    Target url.  

- `method: HTTPMethod = HTTPMethod.GET`    
    HTTP verb. Now support `HTTPMethod.GET` and `HTTPMethod.POST`.  

- `timeout: Optional[SupportsFloat] = None`  
    Timeout for one request attempt in seconds.  

- `retry: Optional[int] = None`  
    Retry times. Notice `retry + 1` is the number of total attempts.  

- `retry_interval: Optional[SupportsFloat] = None`  
    Time interval between two attempts in seconds.  

- `sleep: Optional[SupportsFloat] = None`  
    Sleep time after every completed request (including failing requests). Also be aware of a sleeping request also counts for `concurrency` (see later).  

- `headers: Optional[dict] = None`  
    HTTP headers. It will be merged with `Client` headers (see later).  

- `params: Optional[dict] = None`  
    HTTP query string.  

- `json: Optional[dict] = None`  
    HTTP body encoded in json.  

- `form: Optional[dict] = None`  
    HTTP body encoded in form.  

- `body: Optional[bytes] = None`  
    HTTP body encoded in raw bytes.  

- `text: Optional[str] = None`  
    HTTP body encoded in text.  

- `file: Optional[Union[str, Path]] = None`  
    Send a file in HTTP body. `Path` is the Python `pathlib.Path`.  
    
- `meta: Optional[dict] = None`  
    User-defined meta data, which can be accessed later in `Response`.  

Also be aware of that two `Request`s are equal if all their arguments are the same, but hash values of any two `Request`s are different.

### Initialize Client

Once you have `Request` ready, you need to initialize a `Client`.

    client = Client()

Now let's take a look at the signature of `Client`'s constructor:

    def __init__(self, setting: Optional[dict] = None, *,
                 loop: Optional[asyncio.AbstractEventLoop] = None) -> None

`setting` applies to all `Request` this `Client` processes, but will be overridden by arguments set in specific `Request` (or merged, for `headers`). The default setting is:

    setting: dict = {
        'timeout': 20,
        'retry': 1,
        'retry_interval': 1,

        'headers': CIMultiDict({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/69.0.3497.100 Safari/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,'
                               'ja;q=0.6,zh-TW;q=0.5',
        }),
        'cookies': {},

        'concurrency': 4,
        'concurrency_per_host': 2,
        'sleep_per_request': 1,
    }

There are 3 parameters cannot be set in `Request` (`sleep_per_request` is a synonym for `sleep`). They are:

- `cookies`  
    HTTP cookies.  

- `concurrency`  
    Maximum concurrent `Request`.  

- `concurrency_per_host`  
    Maximum concurrent `Request` towards one host. Host is obtained by `yarl.URL.host`.

### Send Request and Get Response

With `Request` and `Client` in hand, you are ready to do some real stuff.

    future = Client.submit(request)
    response = await future

`Client` supports the async context manager protocol, and has two public methods:

- `def submit(self, requests: Union[Request, Iterable[Request]]) -> asyncio.Future`  
    The result of `Future` will follow the same form as its input, which means if you input a single `Request`, you will get one single `Response`, and if you input a batch of `Request`s, you will get `List[Response]` and its order will correspond to the order of requests.

- `async def close(self) -> None`  
    You must call this method to properly close `Client`.

`ThreadClient` has almost identical API and behaviours. In fact, `ThreadClient` is just a wrapper over `Client`. Differences are summaried as below:

- Support the plain context manager protocol.
- `__init__()` does not take `loop` parameter.
- `close()` is a plain function.
- `submit()` returns a `ThreadFuture`, whose behaviours mimic `concurrent.futures.Future`.

### Process Response

`Response` has following properties and methods:

- `url -> URL`  
    Response url. Note that this url does not necessarily equal to the url of its corresponding `Request`.

- `status -> int`  
    Response status code.  

- `reason -> str`  
    Response reason.  

- `content -> bytes`  
    Response body in raw bytes.  

- `request -> Request`  
    Corresponding `Request`.  

- `meta -> dict`  
    `meta` data in the corresponding `Request`.  

- `text(encoding: Optional[str] = None) -> str`  
    Response body is text. If `encoding` is not set, `Response` will use [cchardet](https://github.com/PyYoshi/cChardet) to detect encoding. If cchardet fails, `'utf-8'` will be assumed.  

- `json() -> Any`  
    Response body as json.  

- `etree(*, html: bool = True) -> etree._ElementTree`  
    Response body as [lxml](https://lxml.de/) etree. If `html` is `True`, body will be first processed by [html5lib](https://github.com/html5lib/html5lib-python).  
    
`text()`, `json()`, `etree()` may sometimes be a expensive operation and they are not likely to be all valid for a single `Response`, so `Response` will compute them lazily and cache the result (use `functools.lru_cache`).

If an exception occurs during processing (including timeout), `Response` will be constructed like:

    Response(
        url=URL(''),
        status=-1,
        reason=repr(exc),
        content=b'',
        request=request,
    )

Same as `Request`, two `Response`s are equal if all their arguments are the same, but hash values of any two `Response`s are different.


----------------------------------------------------------------------------------------------------


## Interpreter

### Inspiration

This interpreter is inspired by [ScalaTest](http://www.scalatest.org/) whose plain English style API really attracts me. The parsing techniques used is based on *[Writing An Interpreter In Go](https://interpreterbook.com/)* with some simplifications.

### Introduction

To build a `interpreter`, you may provide it with a `client` instance or let it creates one by itself. Then you feed a script string to it. Finally, remember to close the `interpreter`. You may use the async context manager as well. See [Overview](#overview) for code examples.

The only piece missing there is about script contexts. Below is the signature of `interpreter.run()`, variables lookup goes through script scope (variables defined by `let`), `local_env`, and `global_env`, in that order.

    async def run(self, source: str,
                  global_env: dict = None,
                  local_env: dict = None) -> Any

There is a [Full Grammar Specification](#full-grammar-specification) in BNF available here, so I will not explain the grammer in detail. I suggests you at least skim that part and get youself familiar with those terms. In following sections I will just explain some points which are either not immediately obvious or are too verbose if written in the specification.

A source script consists of multiple statments (expressions are wrapped in `<expr_stmt>`) and the result of the whole script is just the result of the last statement (`None` for `<let_stmt>`). Every expression has a direct counterpart in Python described as follow, which means you may end with any statement and get a valid Python object back.

    <request_expr>   ->  Request or List[Request]
    <future_expr>    ->  asyncio.Future
    <response_expr>  ->  Response or List[Response]
    <result_expr>    ->  whatever produced by the processing functions

`<then_expr>` is in essential one of theese four expressions above, as we will see later.

A major flaw is you can not define variables equal to some arbitrary Python code, which is because we lack a delimiter for general python expressions. Since Python objects inside expressions can be well delimited by context, I do not see necessarity to conjure more mysterious symbols here. If you want to use pre-defined Python object, just pass them in using `globals()` and `locals()`, like:

    await interpreter.run(script, globals(), locals())

I did not write a threaded version `interpreter` because I do not think it is a good idea to mix threads and coroutines after I wrote `ThreadClient`.

### Some Details About `<request_expr>`

- `<py_object>` in `<request_expr>` should be a `str`, a `yarl.URL`, or an `Iterable` of them.

- `<py_object>` in `<time_interval>`, `<retry>`, and `<sleep>` should be a valid number.

- `<body>` of `<request_field>` will be mapped to concrete body types, such as json, as specified in `<var>`.

    For example:

        get from url with
            set json equals {'k': 'v'} in body

    is equivalent to

        Request(url, json={'k': 'v'})

### Some Details About `<result_expr>`

- `<branch>` in general takes two forms. The first one looks like:

        process responses as bytes with some_function

    All responses will be processed by `some_function`.

    The second form looks like:

        process responses
            whose status equals 200 as bytes with function_A
            whose status equals 500 as bytes with function_B
            otherwise as bytes with function_C

    You can think this form as a series of if-elif-else or a pattern matching.

    Under the hood, plain `as` branches and `otherwise` branches are equivalent to normal `whose` branches whose test part always evaluated to `True`. Therefore the location of `otherwise` matters, it should always be the last branch.

- `<test_op>` maps directly to Python operators as follow:

        A equals B            ->  A == B
        A does not equal B    ->  A != B
        A contains B          ->  B in A
        A does not contain B  ->  B not in A

- `<response_type>` maps directly to `Response` properties or methods:

        bytes  ->  content
        str    ->  text()
        json   ->  json()
        html   ->  etree()
        xml    ->  etree(html=False)

- `<py_object>` after `with` should be a `Callable` has the following signature:

        def some_func(response, obj)

    where `response` is the `Response`, `obj` is the object obtained in `<response_type>` form.

- `<py_block>` after `with` should be a series of Python statements. They will later been wrapped inside a function with the same signature as `some_function` in the last point. This has a few implications:

    1. You may use `response` and `obj` directly.  
   
    2. The indention of the first line does not matter, but the relative indentions between lines should be correct.  
        
    3. You must explicitly `return` a value otherwise the result will be `None`.

### Implicit `<then_expr>`

`<request_expr>`, `<future_expr>`, `<response_expr>`, and `<result_expr>` all can be used as `<then_expr>`, which simply means add `then` before these expressions. A `<then_expr>` may omits one particular component, and the result of the last statement will be inserted into this slot. The mapping from expressions to the component they can omit is:

    <request_expr>   ->  <py_object> (url)
    <future_expr>    ->  <request_expr>
    <response_expr>  ->  <future_expr>
    <result_expr>    ->  <response_expr>

Therefore

    get from 'https://www.baidu.com/'
    then send

is equivalent to

    let request = get from 'https://www.baidu.com/'
    send request

### Full Grammar Specification

    <var> ::= any valid Python identifier
    <http_method> ::= "get from" | "post to"
    <time_interval> ::= <py_object> ("second" | "seconds" | "minute" | "minutes")
    <request_field> ::= "headers" | "query" | "body" | "meta"
    <test_op> ::= "equals" | "does not equal" | "contains" | "does not contain"
    <response_attr> ::= "url" | "status" | "reason"
    <response_type> ::= "bytes" | "str" | "json" | "html" | "xml"
    <py_object> ::= any valid Python object
    <py_block> ::= any valid Python code fragment surrounded by "{{}}"

    <stmt> ::= <let_stmt> | <expr_stmt>
    <let_stmt> ::= "let" <var> "=" <expr_stmt>
    <expr_stmt> ::= <request_expr> | <future_expr> | <response_expr> | <result_expr> | <then_expr>

    <request_expr> ::= <http_method> <py_object> ["with" (<timeout> | <retry> | <sleep> | <set>)+]
    <timeout> ::= "timeout" <time_interval>
    <retry> ::= "retry" [<py_object> ("time" | "times")] ["at" <time_interval> "apart"]
    <sleep> ::= "sleep" <time_interval> "per request"
    <set> ::= "set" <var> "equals" <py_object> "in" <request_field>

    <future_expr> ::= "send" <request_expr>

    <response_expr> ::= wait <future_expr>

    <result_expr> ::= "process" <response_expr> <branch>+
    <branch> ::= [("whose" <response_attr> <test_op> <py_object>) | "otherwise"]
                 "as" <content_type> with (<py_object> | <py_block>)


----------------------------------------------------------------------------------------------------


## Logging, Testing, and Dependencies

`Client` uses the standard logging module with the logger named "client".

AIOClient is tested under CPython 3.7.1 in Windows. All test files are properly constructed so that you can use [Test Discovery](https://docs.python.org/3.7/library/unittest.html#test-discovery) to run all the tests. Because we also have to test circumstances where timeout occurs, these tests may take a few minutes to complete. There may be `unexpected exception`, which is basically because `Client` fails to connect to Google. Nonetheless, as long as all tests success, everything is fine.

Dependencies with their versions being tested against are listed as follow:

    pampy      0.1.9
    yarl       1.3.0
    aiofiles   0.4.0
    aiohttp    3.4.4
    multidict  4.5.2
    cchardet   2.1.4
    html5lib   1.0.1
    lxml       4.2.5
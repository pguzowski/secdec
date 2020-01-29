#ifndef SecDecUtil_integrand_container_hpp_included
#define SecDecUtil_integrand_container_hpp_included

#ifdef SECDEC_WITH_CUDA
    #include <thrust/complex.h>
#endif
#include <complex>
#include <functional>
#include <memory>
#include <sys/mman.h>
#include <atomic>

namespace secdecutil {

    // this error is thrown if the sign check of the deformation (contour_deformation_polynomial.imag() <= 0) fails
    struct sign_check_error : public std::runtime_error { using std::runtime_error::runtime_error; };

    // struct that contains fields that the integrand function can write information to, this gets passed to the gpu and other threads

    struct ResultInfo
    {
        std::atomic<int> filled{0};

        enum class ReturnValue { no_error, sign_check_error_contour_deformation, sign_check_error_positive_polynomial};
        ReturnValue return_value = ReturnValue::no_error;
        int signCheckId;

        void process_errors() const{
            if(return_value == ReturnValue::sign_check_error_contour_deformation){
                throw secdecutil::sign_check_error("\"contour deformation polynomial\", signCheckId=" + std::to_string(signCheckId));
            }
            else if(return_value == ReturnValue::sign_check_error_positive_polynomial){
                throw secdecutil::sign_check_error("\"positive polynomial\", signCheckId=" + std::to_string(signCheckId));
            }
        }

        void clear_errors(){
            return_value = ReturnValue::no_error;
            filled = 0;
        }

        #ifdef SECDEC_WITH_CUDA
        __device__ __host__
        #endif
        void fill_if_empty_threadsafe(const ResultInfo& result_info_new){
          #ifdef __CUDA_ARCH__
            if(not atomicCAS(reinterpret_cast<int*>(&filled), 0, 1)){
          #else
            int tempvariable = 0;
            if(std::atomic_compare_exchange_strong(&filled, &tempvariable, 1)){
          #endif
                return_value = result_info_new.return_value;
                signCheckId = result_info_new.signCheckId;
            }
        }
    };

    template <typename T, typename ...Args>
    class IntegrandContainer {

    private:
        enum Operation { add, subtract, multiply, divide };

    public:

        int number_of_integration_variables;
        std::function<T(Args..., ResultInfo*)> integrand;
        std::shared_ptr<ResultInfo> result_info;
        std::string display_name = "INTEGRAND";

        /*
         *  Call operator
         */
        virtual T operator()(Args... x) const
        {
            return integrand(x..., result_info.get());
        }

        /*
         *  Helper functions
         */
        template<int operation>
        static IntegrandContainer add_subtract_multiply_or_divide(const IntegrandContainer& ic1, const IntegrandContainer& ic2)
        {
            int number_of_integration_variables = std::max(ic1.number_of_integration_variables, ic2.number_of_integration_variables);
            std::function<T(Args..., ResultInfo*)> integrand;

            if (operation == add) {
                integrand = [ic1, ic2] (Args... x, ResultInfo* result_info) { return ic1.integrand(x..., result_info) + ic2.integrand(x..., result_info); };
            } else if (operation == subtract ) {
                integrand = [ic1, ic2] (Args... x, ResultInfo* result_info) { return ic1.integrand(x..., result_info) - ic2.integrand(x..., result_info); };
            } else if (operation == multiply ) {
                integrand = [ic1, ic2] (Args... x, ResultInfo* result_info) { return ic1.integrand(x..., result_info) * ic2.integrand(x..., result_info); };
            } else if ( operation == divide ) {
                integrand = [ic1, ic2] (Args... x, ResultInfo* result_info) { return ic1.integrand(x..., result_info) / ic2.integrand(x..., result_info); };
            }

            return IntegrandContainer(number_of_integration_variables, integrand);
        }

        /*
         * unary operators
         */
        IntegrandContainer operator+() const
        {
            return *this;
        };

        IntegrandContainer operator-() const
        {
            return IntegrandContainer
            (
                number_of_integration_variables,
                [this] (Args... x, ResultInfo* result_info) { return - integrand(x..., result_info); }
            );
        };

        /*
         *  Compound assignment operators
         */
        IntegrandContainer& operator-=(const IntegrandContainer& ic1)
        {
            *this = *this - ic1;
            return *this;
        };

        IntegrandContainer& operator+=(const IntegrandContainer& ic1)
        {
            *this = *this + ic1;
            return *this;
        };

        IntegrandContainer& operator*=(const IntegrandContainer& ic1)
        {
            *this = *this * ic1;
            return *this;
        };
        IntegrandContainer& operator/=(const IntegrandContainer& ic1)
        {
            *this = *this / ic1;
            return *this;
        };

        /*
         *  Binary operators
         */
        friend IntegrandContainer operator-(const IntegrandContainer& ic1, const IntegrandContainer& ic2)
        {
            return add_subtract_multiply_or_divide<subtract>(ic1,ic2);
        };

        friend IntegrandContainer operator+(const IntegrandContainer& ic1, const IntegrandContainer& ic2)
        {
            return add_subtract_multiply_or_divide<add>(ic1,ic2);
        };

        friend IntegrandContainer operator*(const IntegrandContainer& ic1, const IntegrandContainer& ic2)
        {
            return add_subtract_multiply_or_divide<multiply>(ic1,ic2);
        };
        friend IntegrandContainer operator/(const IntegrandContainer& ic1, const IntegrandContainer& ic2)
        {
            return add_subtract_multiply_or_divide<divide>(ic1,ic2);
        };

        /*
         * Constructors
         */
        IntegrandContainer(const int number_of_integration_variables, const std::function<T(Args..., ResultInfo*)>& integrand):
        number_of_integration_variables (number_of_integration_variables), integrand(integrand)
        {
            ResultInfo* result_info_raw = reinterpret_cast<ResultInfo*>(mmap(NULL, sizeof(ResultInfo), PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS,-1,0));
            result_info = std::shared_ptr<ResultInfo>(result_info_raw, [](ResultInfo* result_info_raw){munmap(result_info_raw,sizeof(ResultInfo));});
        };

        // default constructor (the "zero-integrand")
        IntegrandContainer() :
        number_of_integration_variables(0),integrand([](Args... x, ResultInfo* result_info){return T();})
        {
            ResultInfo* result_info_raw = reinterpret_cast<ResultInfo*>(mmap(NULL, sizeof(ResultInfo), PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS,-1,0));
            result_info = std::shared_ptr<ResultInfo>(result_info_raw, [](ResultInfo* result_info_raw){munmap(result_info_raw,sizeof(ResultInfo));});
        };

        void process_errors() const{
            result_info->process_errors();
        }

        void clear_errors(){
            result_info->clear_errors();
        }

        virtual ~IntegrandContainer() = default;
    };

    namespace complex_to_real {

        #define COMPLEX_INTEGRAND_CONTAINER_TO_REAL(OPERATION) \
        template<template<typename ...> class complex_template, typename T, typename... Args> \
        IntegrandContainer<T, Args...> OPERATION(const IntegrandContainer<complex_template<T>, Args...>& ic) \
        { \
            std::function<T(Args...,ResultInfo*)> new_integrand = [ic] (const Args... integration_variables, ResultInfo* result_info){ \
                return ic.integrand(integration_variables..., result_info).OPERATION(); }; \
            return IntegrandContainer<T, Args...>(ic.number_of_integration_variables, new_integrand); \
        }

        COMPLEX_INTEGRAND_CONTAINER_TO_REAL(real)
        COMPLEX_INTEGRAND_CONTAINER_TO_REAL(imag)
        #undef COMPLEX_INTEGRAND_CONTAINER_TO_REAL

    }

    template<typename T, typename Args, typename Pars=double, typename Pars_extra=Pars>
    struct IntegrandContainerWithParameters : IntegrandContainer<T,Args> {
        enum Operation { add, subtract, multiply, divide };
        std::vector<std::vector<Pars>> parameters;
        std::vector<std::vector<Pars*>> parameters_ptr;
        std::vector<std::vector<Pars_extra>> extra_parameters;
        std::function<T(Args,Pars*,ResultInfo*)> integrand_with_parameters;
        std::shared_ptr<ResultInfo> result_info;

        auto get_parameters() -> decltype(parameters_ptr){return parameters_ptr;}
        auto get_extra_parameters() -> decltype(extra_parameters){return extra_parameters;}

        IntegrandContainerWithParameters(const int number_of_integration_variables, const std::function<T(Args,Pars*,ResultInfo*)>& integrand_with_parameters, std::vector<std::vector<Pars>> parameters):
            IntegrandContainer<T,Args>(number_of_integration_variables, [this](Args x){return this->integrand_with_parameters(x,this->parameters[0].data(),this->result_info.get());}),
            integrand_with_parameters(integrand_with_parameters), parameters(parameters), parameters_ptr()
        {
            for(int k = 0; k < parameters.size(); k++){
                parameters_ptr.push_back(std::vector<Pars*>(number_of_integration_variables));
                for(int i = 0; i < number_of_integration_variables; i++){
                    parameters_ptr[k][i] = &this->parameters[k][i];
                }
            }
            ResultInfo* result_info_raw = (ResultInfo*)mmap(NULL, sizeof(ResultInfo), PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS,-1,0);
            result_info = std::shared_ptr<ResultInfo>(result_info_raw, [](ResultInfo* result_info_raw){munmap(result_info_raw,sizeof(ResultInfo));});
        }

        IntegrandContainerWithParameters(const int number_of_integration_variables, const std::function<T(Args, ResultInfo*)>& integrand):
            integrand_with_parameters([integrand](Args x, Pars* p, ResultInfo* result_info){return integrand(x,result_info);}),
            parameters(), extra_parameters(), result_info(std::make_shared<ResultInfo>()) {
                this->number_of_integration_variables = number_of_integration_variables;
            }

        IntegrandContainerWithParameters() :
        IntegrandContainer<T,Args>(0, [](...){return T();}), integrand_with_parameters([](Args x, Pars* p, ResultInfo* result_info){return IntegrandContainer<T,Args>::integrand(x);}),
        parameters(), extra_parameters(), result_info(std::make_shared<ResultInfo>())
        {}

        IntegrandContainerWithParameters(const IntegrandContainerWithParameters& other):
        IntegrandContainerWithParameters(other.number_of_integration_variables, other.integrand_with_parameters, other.parameters){
            result_info = other.result_info;
            extra_parameters = other.extra_parameters;
            IntegrandContainer<T,Args>::display_name = other.display_name;
        }

        template<typename other_T>
        IntegrandContainerWithParameters(const IntegrandContainerWithParameters<other_T,Args,Pars,Pars_extra>& other):
        IntegrandContainerWithParameters(other.number_of_integration_variables, [](Args x, Pars* p, ResultInfo* result_info){return 0;}, other.parameters){
            result_info = other.result_info;
            extra_parameters = other.extra_parameters;
            IntegrandContainer<T,Args>::display_name = other.display_name;
        }

        T operator()(Args x)
        {
            auto dataptr = parameters.size() ? parameters[0].data() : nullptr;
            return integrand_with_parameters(x, dataptr, result_info.get());
        }

        void process_errors() const{
            result_info->process_errors();
        }

        /*
         *  Helper functions
         */
        template<int operation>
        static IntegrandContainerWithParameters add_subtract_multiply_or_divide(const IntegrandContainerWithParameters& ic1, const IntegrandContainerWithParameters& ic2)
        {
            int number_of_integration_variables = std::max(ic1.number_of_integration_variables, ic2.number_of_integration_variables);
            std::function<T(Args)> integrand;

            if (operation == add) {
                integrand = [ic1, ic2] (Args x) { return ic1(x) + ic2(x); };
            } else if (operation == subtract ) {
                integrand = [ic1, ic2] (Args x) { return ic1(x) - ic2(x); };
            } else if (operation == multiply ) {
                integrand = [ic1, ic2] (Args x) { return ic1(x) * ic2(x); };
            } else if ( operation == divide ) {
                integrand = [ic1, ic2] (Args x) { return ic1(x) / ic2(x); };
            }

            return IntegrandContainerWithParameters(number_of_integration_variables, integrand);
        }

        /*
         * unary operators
         */
        IntegrandContainerWithParameters operator+() const
        {
            return *this;
        };

        IntegrandContainerWithParameters operator-() const
        {
            return IntegrandContainerWithParameters
            (
                IntegrandContainer<T,Args>::number_of_integration_variables,
                [this] (Args x, Pars* p) { return - this->integrand_with_parameters(x,p); }, parameters
            );
        };

        /*
         *  Compound assignment operators
         */
        IntegrandContainerWithParameters& operator-=(const IntegrandContainerWithParameters& ic1)
        {
            *this = *this - ic1;
            return *this;
        };

        IntegrandContainerWithParameters& operator+=(const IntegrandContainerWithParameters& ic1)
        {
            *this = *this + ic1;
            return *this;
        };

        IntegrandContainerWithParameters& operator*=(const IntegrandContainerWithParameters& ic1)
        {
            *this = *this * ic1;
            return *this;
        };
        IntegrandContainerWithParameters& operator/=(const IntegrandContainerWithParameters& ic1)
        {
            *this = *this / ic1;
            return *this;
        };

        /*
         *  Binary operators
         */
        friend IntegrandContainerWithParameters operator-(const IntegrandContainerWithParameters& ic1, const IntegrandContainerWithParameters& ic2)
        {
            return add_subtract_multiply_or_divide<subtract>(ic1,ic2);
        };

        friend IntegrandContainerWithParameters operator+(const IntegrandContainerWithParameters& ic1, const IntegrandContainerWithParameters& ic2)
        {
            return add_subtract_multiply_or_divide<add>(ic1,ic2);
        };

        friend IntegrandContainerWithParameters operator*(const IntegrandContainerWithParameters& ic1, const IntegrandContainerWithParameters& ic2)
        {
            return add_subtract_multiply_or_divide<multiply>(ic1,ic2);
        };
        friend IntegrandContainerWithParameters operator/(const IntegrandContainerWithParameters& ic1, const IntegrandContainerWithParameters& ic2)
        {
            return add_subtract_multiply_or_divide<divide>(ic1,ic2);
        };
    };

    namespace complex_to_real {

        #define COMPLEX_INTEGRAND_CONTAINER_TO_REAL(OPERATION) \
        template<template<typename ...> class complex_template, typename T, typename Args, typename Pars> \
        IntegrandContainerWithParameters<T, Args, Pars> OPERATION(const IntegrandContainerWithParameters<complex_template<T>, Args, Pars>& ic) \
        { \
            std::function<T(Args,Pars*,ResultInfo*)> new_integrand = [ic] (Args x, Pars* p, ResultInfo* r){ return ic.integrand_with_parameters(x,p,r).OPERATION(); }; \
            IntegrandContainerWithParameters<T, Args, Pars> new_container = ic; \
            new_container.integrand_with_parameters = new_integrand; \
            return new_container; \
        }

        COMPLEX_INTEGRAND_CONTAINER_TO_REAL(real)
        COMPLEX_INTEGRAND_CONTAINER_TO_REAL(imag)
        #undef COMPLEX_INTEGRAND_CONTAINER_TO_REAL

    }
}

#endif
